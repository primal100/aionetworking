import logging
import datetime

import definitions
import settings
import time

from typing import TYPE_CHECKING, Sequence, AnyStr, Type

if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseMessageManager:
    batch: bool = False
    name: str
    queue_cls = None
    executor = None

    configurable = {
        'store_actions': tuple,
        'print_actions': tuple,
        'interval': float
    }

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], queue=None, **kwargs):
        config = settings.CONFIG.section_as_dict('MessageManager', **cls.configurable)
        logger.info('Found configuration for %s: %s', cls.name,  config)
        if config.get('store_actions', None):
            store_actions_modules = (definitions.ACTIONS[a] for a in config['store_actions'])
            config['store_actions'] = [a.from_config() for a in store_actions_modules]
        if config.get('print_actions', None):
            print_actions_modules = (definitions.ACTIONS[a] for a in config['print_actions'])
            config['print_actions'] = [a.from_config(storage=False) for a in print_actions_modules]
        config.update(kwargs)
        return cls(protocol, queue=queue, **config)

    def __init__(self, protocol: Type[BaseProtocol], queue, store_actions: Sequence=(), print_actions: Sequence=(),
                 interval: int=0.001):
        self.protocol = protocol
        self.queue = queue
        self.interval = interval
        if not self.interval:
            from lib.conf import ConfigurationException
            raise ConfigurationException('Message Manager Interval must be a float greater than 0')
        self.store_actions = store_actions
        self.print_actions = print_actions
        self.process_queue_forever()

    def make_message(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime) -> BaseProtocol:
        return self.protocol(sender, encoded, timestamp=timestamp)

    def process_queue(self):
        raise NotImplementedError

    def process_queue_forever(self):
        if self.interval:
            time.sleep(self.interval)
        try:
            self.process_queue()
        finally:
            self.process_queue_forever()

    def do_actions(self, msgs: Sequence[BaseProtocol]):
        raise NotImplementedError



