import asyncio
import binascii
import logging

from lib import settings
from lib.utils import Record

from typing import TYPE_CHECKING, Sequence, AnyStr
from pathlib import Path
if TYPE_CHECKING:
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseSender:
    logger_name: str = 'sender'
    sender_type: str
    configurable = {
        'interval': float,
    }

    @classmethod
    def get_config(cls, cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Sender', **cls.configurable)
        logger = logging.getLogger(cp.logger_name)
        logger.debug('Found configuration for %s: %s', cls.sender_type, config)
        config.update(kwargs)
        config['logger'] = logger
        return config

    @classmethod
    def from_config(cls, manager: BaseMessageManager, cp=None, queue=None, config=None, **kwargs):
        if not config:
            config = cls.get_config(cp=cp, **kwargs)
        return cls(manager, queue=queue, **config)

    def __init__(self, manager: BaseMessageManager, queue=None, interval: float = 0, logger=None):
        self.logger = logger
        if not self.logger:
            logging.getLogger(self.logger_name)
        self.raw_log = logging.getLogger("%s.raw" % self.logger.name)
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


class BaseNetworkClient(BaseSender):
    sender_type = "Network client"

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

