import asyncio
import datetime
import logging

from lib.utils import log_exception
from lib.protocols.base import BufferProtocol
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
        'action': tuple,
        'preaction': tuple,
        'allowedsenders': tuple,
        'aliases': dict,
        'generate_timestamp': bool,
        'timeout': int
    }

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], cp=None, **kwargs):
        from lib import definitions
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('MessageManager', **cls.configurable)
        log = logging.getLogger(cp.logger_name)
        log.info('Found configuration for %s: %s', cls.name,  config)
        config['action'] = definitions.ACTIONS[config.pop('action')].from_config(cp=cp)
        config['pre_action'] = definitions.ACTIONS[config.pop('preaction')].from_config(cp=cp)
        config.update(kwargs)
        config['logger_name'] = cp.logger_name
        if protocol.supports_responses:
            return TwoWayMessageManager(protocol, **config)
        return OneWayMessageManager(protocol, **config)

    def __init__(self, protocol: Type[BaseProtocol], action = None, pre_action = None,
                 generate_timestamp: bool = False, aliases: Mapping = None, allowedsenders: Sequence = (),
                 timeout:int = 5, logger_name: str = 'receiver'):
        self.log = logging.getLogger(logger_name)
        self.raw_log = logging.getLogger("%s.raw" % logger_name)
        self.msg_log = logging.getLogger("%s.message" % logger_name)
        self.protocol = protocol
        self.generate_timestamp = generate_timestamp
        self.action = action
        self.pre_action = pre_action
        self.aliases = aliases or {}
        self.allowed_senders = allowedsenders
        self.timeout = timeout

    def get_alias(self, sender: str):
        alias = self.aliases.get(str(sender), sender)
        if alias != sender:
            self.log.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        return self.get_alias(other_ip)

    def manage_buffer(self, sender, buffer, timestamp):
        if self.pre_action:
            buffer = BufferProtocol(sender, buffer, timestamp=timestamp, log=self.log)
            self.pre_action.do_one(buffer)

    def manage(self, msgs):
        raise NotImplementedError

    async def close(self):
        self.log.debug('Waiting for %s tasks to complete', self.name)
        try:
            await asyncio.wait_for(self.task_counter.wait(), self.timeout)
        except asyncio.TimeoutError:
            self.log.error("%s closed with %s tasks remaining", self.name, self.task_counter.num)
        self.log.debug('Waiting for %s action to complete', self.name)
        if self.action:
            await self.action.close()
        self.log.debug('Waiting for %s pre-action to complete', self.name)
        if self.pre_action:
            await self.action.close()
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

    def manage(self, msgs):
        raise NotImplementedError


class OneWayMessageManager(BaseReceiverMessageManager):
    name = 'One Way Message Manager'

    def manage(self, msgs):
        self.action.do_many(msgs)
        yield from ()


class TwoWayMessageManager(BaseReceiverMessageManager):
    name = 'Two Way Message Manager'

    def manage(self, msgs):
        for msg in msgs:
            yield msg, self.action.do_one(msg)


class BaseClientMessageManager(BaseMessageManager):

    configurable = {}

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('MessageManager', **cls.configurable)
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
