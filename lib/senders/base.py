import asyncio
import binascii
import logging

from lib import utils, settings

from typing import TYPE_CHECKING, Sequence, AnyStr
from pathlib import Path
if TYPE_CHECKING:
    from lib.messagemanagers.base import BaseMessageManager
else:
    BaseMessageManager = None

logger = logging.getLogger(settings.LOGGER_NAME)
data_logger = logging.getLogger(settings.RAWDATA_LOGGER_NAME)


class BaseSender:
    sender_type: str
    configurable = {
        'interval': float
    }
    receiver_configurable = {
    }

    @classmethod
    def from_config(cls, manager: BaseMessageManager, queue=None, **kwargs):
        config = settings.CONFIG.section_as_dict('Sender', **cls.configurable)
        config.update(settings.CONFIG.section_as_dict('Receiver', **cls.receiver_configurable))
        logger.debug('Found configuration for %s: %s', cls.sender_type, config)
        config.update(kwargs)
        return cls(manager, queue=queue, **config)

    def __init__(self, manager: BaseMessageManager, queue=None, interval: float=0):
        self.manager = manager
        self.protocol = manager.protocol
        self.queue = queue
        self.interval = interval
        if self.queue:
            self.process_queue_task = asyncio.get_event_loop().create_task(self.process_queue_later())
        else:
            self.process_queue_task = None

    @property
    def source(self):
        raise NotImplementedError

    async def process_queue_later(self):
        if self.interval:
            await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            await self.process_queue_later()

    async def process_queue(self):
        msg = await self.queue.wait()
        try:
            logger.debug('Took item from queue')
            await self.send_msg(msg)
        finally:
            logger.debug("Setting task done on queue")
            self.queue.task_done()

    async def close_queue(self):
        if self.queue:
            logger.debug('Closing message queue')
            try:
                timeout = self.interval + 1
                logger.info('Waiting', timeout, 'seconds for queue to empty')
                await asyncio.wait_for(self.queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.error('Queue did not empty in time. Cancelling task with messages in queue.')
            self.process_queue_task.cancel()
            logger.debug('Message queue closed')

    @property
    def dst(self):
        raise NotImplementedError

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_queue()
        await self.stop()

    async def start(self):
        pass

    async def stop(self):
        pass

    async def response(self):
        await self.manager.wait_response()

    async def send_data(self, msg_encoded: bytes):
        raise NotImplementedError

    async def send_msg(self, msg_encoded: bytes):
        logger.debug("Sending message to %s", self.dst)
        data_logger.debug(msg_encoded)
        await self.send_data(msg_encoded)
        logger.debug('Message sent')

    async def send_hex(self, hex_msg:AnyStr):
        await self.send_msg(binascii.unhexlify(hex_msg))

    async def send_msgs(self, msgs:Sequence[bytes]):
        for msg in msgs:
            await self.send_msg(msg)
            await asyncio.sleep(0.001)

    async def send_hex_msgs(self, hex_msgs:Sequence[AnyStr]):
        await self.send_msgs([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    async def encode_and_send_msgs(self, decoded_msgs):
        for decoded_msg in decoded_msgs:
            await self.encode_and_send_msg(decoded_msg)

    async def encode_and_send_msg(self, msg_decoded):
        msg = self.manager.protocol.from_decoded(msg_decoded, sender=self.source)
        await self.send_msg(msg.encoded)

    async def play_recording(self, file_path:Path, immediate:bool=False):
        with file_path.open('rb') as f:
            content = f.read()
        packets = utils.unpack_recorded_packets(content)
        if immediate:
            await self.send_msgs([p[2] for p in packets])
        for microseconds, sender, data in packets:
            if not immediate:
                await asyncio.sleep(microseconds / 1000)
            await self.send_msg(data)


class BaseNetworkClient(BaseSender):
    sender_type = "Network client"

    configurable = BaseSender.configurable.copy()
    configurable.update({
        'src_ip': str,
        'src_port': int
    })
    receiver_configurable = BaseSender.configurable.copy()
    receiver_configurable.update({
        'host': str,
        'port': int,
        'ssl': bool,
    })

    def __init__(self, protocol, queue=None, host: str='127.0.0.1', port: int = 4000,
                 ssl: bool=False, src_ip: str='', src_port: int=0, **kwargs):
        super(BaseNetworkClient, self).__init__(protocol, queue=queue, **kwargs)
        self.host = host
        self.port = port
        self.localaddr = (src_ip, src_port) if src_ip else None
        self.ssl = ssl

    @property
    def source(self) -> str:
        return self.host

    @property
    def dst(self) -> str:
        return "%s:%s" % (self.host, self.port)

    async def open_connection(self):
        raise NotImplementedError

    async def close_connection(self):
        raise NotImplementedError

    async def send_data(self, encoded_data:bytes):
        raise NotImplementedError

    async def start(self):
        logger.info("Opening %s connection to %s", self.sender_type, self.dst)
        await self.open_connection()
        logger.info("Connection open")

    async def stop(self):
        logger.info("Closing %s connection to %s", self.sender_type, self.dst)
        await self.close_connection()
        logger.info("Connection closed")
