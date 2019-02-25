import asyncio
import binascii
import logging
import ssl

from lib.conf import ConfigurationException
from lib import utils, settings

from typing import TYPE_CHECKING, Sequence, AnyStr
from pathlib import Path
if TYPE_CHECKING:
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseSender:
    sender_type: str
    configurable = {
        'interval': float
    }
    receiver_configurable = {
    }

    @classmethod
    def from_config(cls, manager: BaseMessageManager, cp=None, queue=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Sender', **cls.configurable)
        config.update(cp.section_as_dict('Receiver', **cls.receiver_configurable))
        log = logging.getLogger(cp.logger_name)
        log.debug('Found configuration for %s: %s', cls.sender_type, config)
        config.update(kwargs)
        config['logger_name'] = cp.logger_name
        return cls(manager, queue=queue, **config)

    def __init__(self, manager: BaseMessageManager, queue=None, interval: float=0, logger_name: str = 'sender'):
        self.log = logging.getLogger(logger_name)
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
            self.log.debug('Took item from queue')
            await self.send_msg(msg)
        finally:
            self.log.debug("Setting task done on queue")
            self.queue.task_done()

    async def close_queue(self):
        if self.queue:
            self.log.debug('Closing message queue')
            try:
                timeout = self.interval + 1
                self.log.info('Waiting', timeout, 'seconds for queue to empty')
                await asyncio.wait_for(self.queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                self.log.error('Queue did not empty in time. Cancelling task with messages in queue.')
            self.process_queue_task.cancel()
            self.log.debug('Message queue closed')

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
        self.log.debug("Sending message to %s", self.dst)
        self.raw_log.debug(msg_encoded)
        await self.send_data(msg_encoded)
        self.log.debug('Message sent')

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
    ssl_allowed: bool = False

    configurable = BaseSender.configurable.copy()
    configurable.update({
        'srcip': str,
        'srcport': int,
        'certrequired': bool,
        'hostnamecheck': bool,
        'cafile': Path,
        'capath': Path,
        'cadata': str
    })
    receiver_configurable = BaseSender.configurable.copy()
    receiver_configurable.update({
        'host': str,
        'port': int,
        'ssl': bool,
    })

    def __init__(self, protocol, queue=None, host: str = '127.0.0.1', port: int = 4000,
                 ssl: bool = False, srcip: str = '', srcport: int = 0, cafile: Path= None,
                 capath: Path=None, cadata: str=None, certrequired: bool=True,
                          hostnamecheck: bool=True, **kwargs):
        super(BaseNetworkClient, self).__init__(protocol, queue=queue, **kwargs)
        self.host = host
        self.port = port
        self.localaddr = (srcip, srcport) if srcip else None
        self.ssl = ssl
        if self.ssl_allowed:
            self.ssl = self.manage_ssl_params(ssl, cafile, capath, cadata, certrequired, hostnamecheck)
        elif ssl:
            self.log.error('SSL is not supported for %s', self.sender_type)
            raise ConfigurationException('SSL is not supported for %s' + self.sender_type)
        else:
            self.ssl = None

    def manage_ssl_params(self, context, cafile: Path, capath: Path, cadata: str, certrequired: bool,
                          hostnamecheck: bool):
        if context:
            self.log.info("Setting up SSL")
            if context is True:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS)

                context.verify_mode = ssl.CERT_REQUIRED if certrequired else ssl.CERT_NONE
                context.check_hostname = hostnamecheck

                if context.verify_mode != ssl.CERT_NONE:
                    if cafile or capath or cadata:
                        locations = {'cafile': str(cafile) if cafile else None,
                                     'capath': str(capath) if capath else None,
                                     'cadata': cadata}
                        context.load_verify_locations(**locations)
                        self.log.info("Verifying SSL certs with: %s", locations)
                    else:
                        context.load_default_certs(ssl.Purpose.SERVER_AUTH)
                        self.log.info("Verifying SSL certs with: %s", ssl.get_default_verify_paths())
            self.log.info("SSL Context loaded")
            return context
        else:
            self.log.info("SSL is not enabled")
            return None

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
        self.log.info("Opening %s connection to %s", self.sender_type, self.dst)
        await self.open_connection()
        self.log.info("Connection open")

    async def stop(self):
        self.log.info("Closing %s connection to %s", self.sender_type, self.dst)
        await self.close_connection()
        self.log.info("Connection closed")
