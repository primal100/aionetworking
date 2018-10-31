import logging
import datetime

import definitions
import settings

from typing import TYPE_CHECKING, Sequence, AnyStr, Type

if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageFromNotAuthorizedHost(Exception):
    pass


def raise_message_from_not_authorized_host(sender, allowed_senders):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s"
    args = (sender, allowed_senders)
    logger.error(msg, *args)
    raise MessageFromNotAuthorizedHost(msg % args)


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
    def from_config(cls, protocol: Type[BaseProtocol], queue=None, **kwargs):
        config = settings.CONFIG.section_as_dict('MessageManager', **cls.configurable)
        logger.debug('Found configuration for %s: %s', cls.name,  config)
        store_actions_modules = (definitions.ACTIONS[a] for a in config['store_actions'])
        print_actions_modules = (definitions.ACTIONS[a] for a in config['print_actions'])
        config['store_actions'] = [a.from_config() for a in store_actions_modules]
        config['print_actions'] = [a.from_config(storage=False) for a in print_actions_modules]
        config.update(kwargs)
        return cls(protocol, queue=queue, **config)

    def __init__(self, protocol: Type[BaseProtocol], queue, store_actions: Sequence=(), print_actions: Sequence=(),
                 allowed_senders: Sequence=(), generate_timestamp: bool=False, aliases: Sequence=None, interval: int=0.001):
        self.protocol = protocol
        self.allowed_senders = allowed_senders
        self.aliases = aliases or None
        self.generate_timestamp = generate_timestamp
        self.interval = interval
        if not self.interval:
            from lib.conf import ConfigurationException
            raise ConfigurationException('Message Manager Interval must be a float greater than 0')
        self.store_actions = store_actions
        self.print_actions = print_actions
        self.queue = queue

    def get_alias(self, sender: str):
        alias = self.aliases.get(sender, sender)
        if alias != sender:
            logger.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, sender: str):
        if self.allowed_senders and sender not in self.allowed_senders:
            raise_message_from_not_authorized_host(sender, self.allowed_senders)
        if self.allowed_senders:
            logger.debug('Sender is in allowed senders')
        return self.get_alias(sender)

    def make_message(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime) -> BaseProtocol:
        return self.protocol(sender, encoded, timestamp=timestamp)

    async def manage_message(self, sender: str, encoded: AnyStr):
        logger.debug('Managing message from %s', sender)
        host = self.check_sender(sender)
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp: %s', timestamp)
        else:
            timestamp = None
        logger.debug('Adding message from %s to queue', host)
        await self.add_to_queue(host, encoded, timestamp)

    async def process_queue_forever(self):
        while True:
            item = await self.queue.get()
            try:
                logger.debug('Took item from queue')
                sender, encoded, timestamp = item
                msg = self.make_message(sender, encoded, timestamp)
                if not msg.filter():
                    self.do_actions([msg])
                else:
                    logger.debug("Message was filtered out")
            finally:
                logger.debug("Setting task done on queue")
                self.queue.task_done()

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
        finally:
            try:
                if msgs:
                    self.do_actions(msgs)
            finally:
                for msg in msgs:
                    logger.debug("Setting task done on queue")
                    self.queue.task_done()

    async def add_to_queue(self, host: str, encoded: AnyStr, timestamp: datetime.datetime):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def do_actions(self, msgs: Sequence[BaseProtocol]):
        raise NotImplementedError



