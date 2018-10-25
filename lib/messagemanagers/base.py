import logging
import datetime
import asyncio
from typing import Sequence

from lib.protocols.base import BaseProtocol
import definitions

logger = logging.getLogger(definitions.LOGGER_NAME)


class MessageFromNotAuthorizedHost(Exception):
    pass


def raise_message_from_not_authorized_host(sender, allowed_senders):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s" % (sender, allowed_senders)
    logger.error(msg)
    raise MessageFromNotAuthorizedHost(msg)


class BaseMessageManager:
    batch: bool = False
    name: str

    configurable = {
        'store_actions': tuple,
        'print_actions': tuple,
        'generate_timestamp': bool,
        'aliases': dict,
        'interval': float
    }

    @classmethod
    def from_config(cls, protocol, queue=None, **kwargs):
        config = definitions.CONFIG.section_as_dict('MessageManager', **cls.configurable)
        logger.debug('Found configuration for', cls.name, ':', config)
        config.update(kwargs)
        return cls(protocol, queue=queue, **kwargs)

    def __init__(self, protocol, queue=None, store_actions=(), print_actions=(), allowed_senders=(),
                 generate_timestamp=False, aliases=None, interval=0):
        self.protocol = protocol
        self.allowed_senders = allowed_senders
        self.aliases = aliases or None
        self.generate_timestamp = generate_timestamp
        self.interval = interval
        self.store_actions = store_actions
        self.print_actions = print_actions
        self.queue = queue or asyncio.Queue()
        self.process_queue_task = asyncio.get_event_loop().create_task(self.process_queue_later())

    def get_alias(self, sender):
        alias = self.aliases.get(sender, sender)
        if alias != sender:
            logger.debug('Alias found for', sender, ':', alias)
        return alias

    def check_sender(self, sender):
        if self.allowed_senders and sender not in self.allowed_senders:
            raise_message_from_not_authorized_host(sender, self.allowed_senders)
        if self.allowed_senders:
            logger.debug('Sender is in allowed senders.')
        return self.get_alias(sender)

    def make_message(self, sender, encoded, timestamp):
        return self.protocol(sender, encoded, timestamp=timestamp)

    async def manage_message(self, sender, encoded):
        logger.debug('Managing message from', sender)
        host = self.check_sender(sender)
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp:', timestamp)
        else:
            timestamp = None
        logger.debug('Adding message from', host, 'to asyncio queue')
        await self.queue.put((host, encoded, timestamp))

    async def process_queue_later(self):
        if self.interval:
            await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            await self.process_queue_later()

    async def process_queue(self):
        msgs = []
        try:
            while not self.queue.empty():
                item = self.queue.get_nowait()
                logger.debug('Took item from queue')
                sender, encoded, timestamp = item
                msg = self.make_message(sender, encoded, timestamp)
                if not msg.filter():
                    msgs.append(msg)
                else:
                    logger.debug("Message was filtered out")
            self.do_actions(msgs)
        finally:
            for msg in msgs:
                logger.debug("Setting task done on queue")
                self.queue.task_done()

    async def close(self):
        logger.info('Closing Batch Message Manager')
        try:
            timeout = self.interval + 1
            logger.info('Waiting %s seconds for queue to empty' % timeout)
            await asyncio.wait_for(self.queue.join(), timeout=timeout + 1)
            logger.info('Queue empty. Cancelling task')
        except asyncio.TimeoutError:
            logger.error('Queue did not empty. Cancelling task with messages in queue.')
        self.process_queue_task.cancel()
        logger.info('Batch Message Manager closed')

    def do_actions(self, msgs: Sequence[BaseProtocol]):
        raise NotImplementedError



