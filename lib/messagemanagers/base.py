import asyncio
import logging
import datetime

from lib.conf import ConfigurationException
from lib.utils import cached_property
import settings

from typing import TYPE_CHECKING, Sequence, AnyStr, Type
from pathlib import Path

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
        'record': bool,
        'record_file': Path,
    }

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], queue=None, **kwargs):
        import definitions
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

    def __init__(self, protocol: Type[BaseProtocol], queue, store_actions: Sequence=(), print_actions: Sequence=()):
        self.protocol = protocol
        self.queue = queue
        self.store_actions = store_actions
        self.print_actions = print_actions

    def make_messages(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime) -> Sequence[BaseProtocol]:
        return self.protocol.from_buffer(sender, encoded, timestamp=timestamp)

    def process_queue(self):
        raise NotImplementedError

    async def task_done(self, tasks: Sequence[asyncio.Task], num_times=1):
        for task in tasks:
            await task
        for i in range(0, num_times):
            logger.debug("All actions complete. Setting task done on queue")
            self.queue.task_done()

    async def process_queue_forever(self):
        try:
            await self.process_queue()
        finally:
            await self.process_queue_forever()

    @cached_property
    def has_actions_no_decoding(self) -> bool:
        return any([not a.requires_decoding for a in self.store_actions]) or any([not a.requires_decoding for a in self.print_actions])

    @cached_property
    def requires_decoding(self) -> bool:
        return any([a.requires_decoding for a in self.store_actions]) or any([a.requires_decoding for a in self.print_actions])


