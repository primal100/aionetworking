import asyncio
import binascii
import logging

from lib.conf import RawStr
from lib import settings
from lib.networking.ssl import get_client_context
from lib.utils import Record

from typing import TYPE_CHECKING, Sequence, AnyStr
from pathlib import Path
if TYPE_CHECKING:
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseSender:
    sender_type: str
    configurable = {
        'interval': float,
    }

    @classmethod
    def from_config(cls, manager: BaseMessageManager, cp=None, queue=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Sender', **cls.configurable)
        config.update(cp.section_as_dict('Receiver'))
        log = logging.getLogger(cp.logger_name)
        log.debug('Found configuration for %s: %s', cls.sender_type, config)
        config.update(kwargs)
        config['logger_name'] = cp.logger_name
        return cls(manager, queue=queue, **config)

    def __init__(self, manager: BaseMessageManager, queue=None, interval: float=0, logger_name: str = 'sender'):
        self.logger = logging.getLogger(logger_name)
        self.raw_log = logging.getLogger("%s.raw" % logger_name)
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
            self.logger.debug('Took item from queue')
            await self.send_msg(msg)
        finally:
            self.logger.debug("Setting task done on queue")
            self.queue.task_done()

    async def close_queue(self):
        if self.queue:
            self.logger.debug('Closing message queue')
            try:
                timeout = self.interval + 1
                self.logger.info('Waiting', timeout, 'seconds for queue to empty')
                await asyncio.wait_for(self.queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.error('Queue did not empty in time. Cancelling task with messages in queue.')
            self.process_queue_task.cancel()
            self.logger.debug('Message queue closed')

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

    async def send_data(self, msg_encoded: bytes, **kwargs):
        raise NotImplementedError

    async def send_msg(self, msg_encoded: bytes, **kwargs):
        self.logger.debug("Sending message to %s", self.dst)
        self.raw_log.debug(msg_encoded)
        await self.send_data(msg_encoded, **kwargs)
        self.logger.debug('Message sent')

    async def send_hex(self, hex_msg: AnyStr):
        await self.send_msg(binascii.unhexlify(hex_msg))

    async def send_msgs_sequential(self, msgs:Sequence[bytes]):
        for msg in msgs:
            await self.send_msg(msg)
            await asyncio.sleep(0.001)

    async def send_msgs_parallel(self, msgs: Sequence[bytes]):
        tasks = []
        for msg in msgs:
            task = asyncio.create_task(self.send_msg(msg))
            tasks.append(task)
        await asyncio.wait(tasks)

    async def send_msgs(self, msgs):
        await self.send_msgs_sequential(msgs)

    async def send_hex_msgs(self, hex_msgs:Sequence[AnyStr]):
        await self.send_msgs([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    async def encode_and_send_msgs(self, decoded_msgs):
        for decoded_msg in decoded_msgs:
            await self.encode_and_send_msg(decoded_msg)

    def encode_msg(self, msg_decoded):
        msg_obj = self.manager.protocol.from_decoded(msg_decoded, sender=self.source)
        return msg_obj.encoded

    async def encode_and_send_msg(self, msg_decoded):
        msg_encoded = self.encode_msg(msg_decoded)
        await self.send_msg(msg_encoded)

    async def play_recording(self, file_path: Path, hosts=(), timing: bool=True):
        self.logger.debug("Playing recording from file %s", file_path)
        for packet in Record.from_file(file_path):
            if (not hosts or packet['host'] in hosts) and not packet['sent_by_server']:
                if timing:
                    await asyncio.sleep(packet['seconds'])
                self.logger.debug('Sending msg with %s bytes', len(packet['data']))
                await self.send_msg(packet['data'])
        self.logger.debug("Recording finished")


class BaseNetworkClient(BaseSender):
    sender_type = "Network client"
    ssl_allowed: bool = False

    configurable = BaseSender.configurable.copy()
    configurable.update({
        'host': str,
        'port': int,
        'srcip': str,
        'srcport': int,
    })

    def __init__(self, protocol, queue=None, host: str = '127.0.0.1', port: int = 4000,
                 srcip: str = '', srcport: int = None, **kwargs):
        super(BaseNetworkClient, self).__init__(protocol, queue=queue, **kwargs)
        self.host = host
        self.port = port
        self.localaddr = (srcip, srcport) if srcip else None

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

    async def send_data(self, encoded_data:bytes, **kwargs):
        raise NotImplementedError

    async def start(self):
        self.logger.info("Opening %s connection to %s", self.sender_type, self.dst)
        await self.open_connection()
        self.logger.info("Connection open")

    async def stop(self):
        self.logger.info("Closing %s connection to %s", self.sender_type, self.dst)
        await self.close_connection()
        self.logger.info("Connection closed")


class SSLSupportedNetworkClient(BaseNetworkClient):
    configurable = BaseNetworkClient.configurable.copy()
    configurable.update({
        'ssl': bool,
        'sslcert': Path,
        'sslkey': Path,
        'sslkeypassword': str,
        'certrequired': bool,
        'hostnamecheck': bool,
        'servercertfile': Path,
        'servercertspath': Path,
        'servercertsdata': str,
        'sslhandshaketimeout': int
    })

    def __init__(self, *args, ssl: bool = False, sslcert: Path = None, sslkey: Path = None, sslkeypassword: str = None,
                servercertfile: Path= None, servercertspath: Path=None, servercertsdata: str=None, certrequired: bool=True,
                hostnamecheck: bool=True, sslhandshaketimeout: int=None, **kwargs):
        super(SSLSupportedNetworkClient, self).__init__(*args, **kwargs)
        self.ssl_handshake_timeout = sslhandshaketimeout
        self.ssl = get_client_context(ssl, sslcert, sslkey, sslkeypassword, servercertfile, servercertspath,
                                      servercertsdata, certrequired, hostnamecheck, self.logger)
