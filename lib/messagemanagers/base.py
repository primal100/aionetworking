import asyncio
import traceback
import logging
import datetime

from lib.utils import cached_property, log_exception
from lib.protocols.raw import RawDataProtocol
from lib.wrappers import executors
from lib import settings

from typing import TYPE_CHECKING, Sequence, AnyStr, Type
from pathlib import Path

if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None


logger = settings.get_logger('main')
raw_logger = settings.get_logger('raw')
msg_logger = settings.get_logger('message')


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
        'executor': str,
        'max_workers': int
    }

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], **kwargs):
        from lib import definitions
        config = settings.CONFIG.section_as_dict('MessageManager', **cls.configurable)
        logger.info('Found configuration for %s: %s', cls.name,  config)
        executor, max_workers = config.pop('executor', None), config.pop('max_workers', None)
        if executor == 'thread':
            executor = executors.ThreadedTaskExecutor(max_workers=max_workers)
        elif executor == 'process':
            executor = executors.ProcessTaskExecutor(max_workers=max_workers)
        else:
            executor = None
        batch = config.pop('batch', False)
        supports_responses = not batch and protocol.supports_responses
        config['actions'] = []
        if config.get('store_actions', None):
            store_actions_modules = (definitions.ACTIONS[a] for a in config.pop('store_actions'))
            config['actions'] += [a.from_config(batch=batch, executor=executor) for a in store_actions_modules]
        if config.get('print_actions', None):
            print_actions_modules = (definitions.ACTIONS[a] for a in config.pop('print_actions'))
            config['actions'] += [a.from_config(executor=executor, storage=False) for a in print_actions_modules]
        config.update(kwargs)
        return cls(protocol, supports_responses=supports_responses, **config)

    def __init__(self, protocol: Type[BaseProtocol], supports_responses:bool=False, actions: Sequence=(),
                 generate_timestamp: bool=False, aliases: Sequence=(), allowed_senders: Sequence=()):
        self.protocol = protocol
        self.generate_timestamp = generate_timestamp
        self.actions = {'raw': {'store': {}, 'print': {}}, 'protocol': {'store': {}, 'print': {}}}
        self.all_actions = actions
        for action in self.all_actions:
            if action.requires_decoding and action.storage:
                self.actions['protocol']['store'][action.action_name] = action
            elif action.requires_decoding and not action.storage:
                self.actions['protocol']['print'][action.action_name] = action
            elif action.storage:
                self.actions['raw']['store'][action.action_name] = action
            else:
                self.actions['raw']['print'][action.action_name] = action
        self.aliases = aliases or {}
        self.allowed_senders = allowed_senders
        self.supports_responses = supports_responses

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

    def handle_message(self, sender: str, data: AnyStr):
        logger.debug("Handling buffer for %s", extra={'sender': sender})
        raw_logger.debug(data, extra={'sender': sender})
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp: %s', timestamp, extra={'sender': sender})
        else:
            timestamp = None
        msgs = self.make_messages(sender, data, timestamp)
        return self.manage(sender, msgs)

    def make_raw_message(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime):
        return self.raw_data_protocol.from_buffer(sender, encoded, timestamp=timestamp)[0]

    def make_messages(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime) -> Sequence[BaseProtocol]:
        try:
            msgs = self.protocol.from_buffer(sender, encoded, timestamp=timestamp)
            for msg in msgs:
                msg_logger.debug('', extra={'msg': msg, 'sender': sender})
            return msgs
        except Exception as e:
            logger.error(e)
            return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug('Exiting %s', self.name)
        if exc_type:
            error = traceback.format_exception(exc_type, exc_val, exc_tb)
            logger.error('\n'.join(error))
        await self.cleanup()
        logger.debug('Exited from %s', self.name)

    @staticmethod
    def filter(msg, **logextra):
        filtered = msg.filtered()
        if filtered:
            logger.debug("Message was filtered out", extra={logextra)
        return filtered

    async def run(self, started_event):
        raise NotImplementedError

    @cached_property
    def has_actions_no_decoding(self) -> bool:
        return bool(self.actions['raw']['print'] or self.actions['raw']['store'])

    @cached_property
    def requires_decoding(self) -> bool:
        return bool(self.actions['protocol']['print'] or self.actions['protocol']['store'])

    async def manage(self, sender, msgs):
        raise NotImplementedError

    async def cleanup(self):
        logger.debug('Running message manager cleanup')
        for action in self.all_actions:
            await action.close()
        logger.debug('Message manager cleanup completed')
