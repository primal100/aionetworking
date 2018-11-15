import logging
import datetime

from lib.utils import cached_property
from lib.protocols.raw import RawDataProtocol
from lib.wrappers.executors import BaseTaskExecutor, TaskExecutor
import settings

from typing import TYPE_CHECKING, Sequence, AnyStr, Type
from pathlib import Path

if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)
data_logger = logging.getLogger(settings.RAWDATA_LOGGER_NAME)


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
    queue_cls = None
    executor = None
    raw_data_protocol: Type[BaseProtocol] = RawDataProtocol

    configurable = {
        'store_actions': tuple,
        'print_actions': tuple,
        'record': bool,
        'record_file': Path,
        'allowed_senders': tuple,
        'aliases': dict,
        'generate_timestamp': bool,
    }

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], **kwargs):
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
        return cls(protocol, **config)

    def __init__(self, protocol: Type[BaseProtocol], store_actions: Sequence=(), print_actions: Sequence=(),
                 generate_timestamp: bool=False, aliases: Sequence=(), allowed_senders: Sequence=(),
                 executor_cls: Type[BaseTaskExecutor]=TaskExecutor, max_workers: int=None):
        self.protocol = protocol
        self.executor = executor_cls(max_workers=max_workers)
        self.generate_timestamp = generate_timestamp
        self.store_actions = store_actions
        self.print_actions = print_actions
        self.aliases = aliases or {}
        self.allowed_senders = allowed_senders

    def get_alias(self, sender: str):
        alias = self.aliases.get(sender, sender)
        if alias != sender:
            logger.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        if self.allowed_senders and other_ip not in self.allowed_senders:
            raise_message_from_not_authorized_host(other_ip, self.allowed_senders)
        if self.allowed_senders:
            logger.debug('Sender is in allowed senders')
        return self.get_alias(other_ip)

    async def handle_message(self, sender: str, data: AnyStr):
        logger.debug("Received msg from %s", sender)
        data_logger.debug(data)

        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp: %s', timestamp)
        else:
            timestamp = None
        return await self.manage(sender, data, timestamp)

    def make_raw_message(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime):
        return self.raw_data_protocol.from_buffer(sender, encoded, timestamp=timestamp)[0]

    def make_messages(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime) -> Sequence[BaseProtocol]:
        return self.protocol.from_buffer(sender, encoded, timestamp=timestamp)

    async def task_done(self, tasks: Sequence, num_times=1):
        logger.debug('checking task done')
        for task in tasks:
            logger.debug('waiting on task')
            await task
            logger.debug('checking for exception')
            e = task.exception()
            logger.debug('no exception')
            if e:
                logger.error(e)
        for i in range(0, num_times):
            logger.debug("All actions complete. Setting task done on queue")
            self.queue.task_done()


    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(exc_type)
            logger.error(exc_val)
            logger.error(exc_tb)

    async def run(self, started_event):
        raise NotImplementedError

    @cached_property
    def has_actions_no_decoding(self) -> bool:
        return any([not a.requires_decoding for a in self.store_actions]) or any([not a.requires_decoding for a in self.print_actions])

    @cached_property
    def requires_decoding(self) -> bool:
        return any([a.requires_decoding for a in self.store_actions]) or any([a.requires_decoding for a in self.print_actions])

    def manage(self, sender, data, timestamp):
        raise NotImplementedError
