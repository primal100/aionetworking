import asyncio
import datetime
import logging

from lib.utils import log_exception, plural
from lib import settings
from .exceptions import MessageFromNotAuthorizedHost

from typing import TYPE_CHECKING, Sequence, Mapping, Type, AnyStr
if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None


def raise_message_from_not_authorized_host(sender, allowed_senders, logger):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s"
    args = (sender, allowed_senders)
    logger.error(msg, *args)
    raise MessageFromNotAuthorizedHost(msg % args)


class BaseMessageManager:
    name: str

    configurable = {
        'actions': tuple,
        'allowedsenders': tuple,
        'aliases': dict,
        'generate_timestamp': bool,
    }

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], cp = None, **kwargs):
        from lib import definitions
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('MessageManager', **cls.configurable)
        log = logging.getLogger(cp.logger_name)
        log.info('Found configuration for %s: %s', cls.name,  config)
        action_modules = (definitions.ACTIONS[action] for action in config.pop('actions'))
        config['actions'] = [action.from_config() for action in action_modules]
        config.update(kwargs)
        config['logger_name'] = cp.logger_name
        if protocol.supports_responses:
            return TwoWayMessageManager(protocol, **config)
        return OneWayMessageManager(protocol, **config)

    def __init__(self, protocol: Type[BaseProtocol], actions: Sequence = (),
                 generate_timestamp: bool = False, aliases: Mapping = None, allowedsenders: Sequence = (),
                 logger_name: str = 'receiver'):
        self.log = logging.getLogger(logger_name)
        self.raw_log = logging.getLogger("%s.raw" % logger_name)
        self.msg_log = logging.getLogger("%s.message" % logger_name)
        self.protocol = protocol
        self.generate_timestamp = generate_timestamp
        self.actions = actions
        self.aliases = aliases or {}
        self.allowed_senders = allowedsenders

    def get_alias(self, sender: str):
        alias = self.aliases.get(sender, sender)
        if alias != sender:
            self.log.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        return self.get_alias(other_ip)

    def handle_message(self, sender: str, data: AnyStr):
        self.log.debug("Handling buffer from %s", sender, extra={'sender': sender})
        self.raw_log.debug(data, extra={'sender': sender})
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            self.log.debug('Generated timestamp: %s', timestamp, extra={'sender': sender})
        else:
            timestamp = None
        msgs = self.make_messages(sender, data, timestamp)
        return self.manage(sender, msgs)

    def make_messages(self, sender: str, encoded: AnyStr, timestamp: datetime.datetime) -> Sequence[BaseProtocol]:
        try:
            msgs = self.protocol.from_buffer(sender, encoded, timestamp=timestamp, log=self.log)
            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug('Buffer contains %s', plural(len(msgs), 'message'))
                for msg in msgs:
                    self.msg_log.debug('', extra={'msg_obj': msg, 'sender': sender})
            return msgs
        except Exception as e:
            self.log.error(e)
            return None

    def filter(self, msg, **log_extra):
        filtered = msg.filtered()
        if filtered:
            self.log.debug("Message was filtered out", extra=log_extra)
        return filtered

    async def manage(self, sender, msgs):
        raise NotImplementedError

    async def close(self):
        self.log.debug('Closing %s', self.name)
        for action in self.actions:
            await action.close()
        self.log.debug('%s closed', self.name)


class BaseReceiverMessageManager(BaseMessageManager):

    configurable = BaseMessageManager.configurable
    configurable.update({
        'allowedsenders': tuple,
    })

    def check_sender(self, other_ip):
        if self.allowed_senders and other_ip not in self.allowed_senders:
            raise_message_from_not_authorized_host(other_ip, self.allowed_senders, self.log)
        if self.allowed_senders:
            self.log.debug('%s is in allowed senders', other_ip)
        return super(BaseReceiverMessageManager,self).check_sender(other_ip)

    async def manage(self, sender, msgs):
        raise NotImplementedError


class OneWayMessageManager(BaseReceiverMessageManager):
    name = 'One Way Message Manager'

    async def do_actions(self, msgs):
        for action in self.actions:
            await action.do_many(msgs)

    async def wait_actions(self, **logs_extra):
        for action in self.actions:
            await action.wait_complete(**logs_extra)

    async def manage(self, sender, msgs):
        msgs = [msg for msg in msgs if not msg.filter()]
        await self.do_actions(msgs)
        await self.wait_actions(sender=sender)


class TwoWayMessageManager(BaseReceiverMessageManager):
    name = 'Two Way Message Manager'

    def log_task_exceptions(self, task):
        exc = task.exception()
        if exc:
            self.log.error(log_exception(exc))

    def do_actions(self, msg):
        tasks = []
        for action in self.actions:
            fut = asyncio.ensure_future(action.do_one(msg))
            fut.add_done_callback(self.log_task_exceptions)
            tasks.append(fut)
        return tasks

    async def manage(self, sender, msgs):
        responses = []
        tasks = []
        for msg in msgs:
            if not msg.filter():
                task_set = self.do_actions(msg)
                tasks.append((msg, task_set))
        for msg, task_set in tasks:
            responses.append(msg.get_response(task_set))
        return responses


class BaseClientMessageManager(BaseMessageManager):

    configurable = {}

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], **kwargs):
        config = settings.CONFIG.section_as_dict('MessageManager', **cls.configurable)
        config.update(kwargs)
        return cls(protocol, **config)


class ClientOneWayMessageManager(BaseClientMessageManager):
    name = 'Client One Way Message Manager'

    def handle_message(self, sender: str, data: AnyStr):
        raise NotImplementedError


class ClientTwoWayMessageManager(BaseMessageManager):
    name = 'Client Two Way Message Manager'

    def __init__(self, *args, **kwargs):
        super(ClientTwoWayMessageManager, self).__init__(*args, **kwargs)
        self.queue = asyncio.Queue()

    async def manage(self, sender, msgs):
        for msg in msgs:
            await self.queue.put((sender, msg))

    async def wait_response(self):
        await self.queue.get()
