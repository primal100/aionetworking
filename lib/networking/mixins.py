from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import field
from functools import partial

from pydantic.types import IPvAnyNetwork

from .exceptions import MessageFromNotAuthorizedHost
from lib.conf.logging import Logger
from lib.utils_logging import p
from .asyncio_protocols import BaseReceiverProtocol, BaseSenderProtocol

from typing import TYPE_CHECKING, ClassVar, List

if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass


@dataclass
class NetworkProtocolMixin(ABC):
    sock = (None, None)
    own = ''
    alias = ''
    peer = None
    peer_ip = None
    peer_port = 0
    transport = None

    _connections: ClassVar = {}

    @property
    @abstractmethod
    def client(self): ...

    @property
    @abstractmethod
    def server(self): ...

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.new_connection()
            self._connections[self.peer] = self
            self.logger.debug('Connection opened. There %s now %s.', p.plural_verb('is', p.num(len(self._connections))),
                              p.no('active connection'))

    def close_connection(self):
        pass

    def connection_lost(self, exc):
        self.logger.connection_finished(exc)
        self.close_connection()
        self._connections.pop(self.peer, None)

    @property
    def connection_context(self):
        return {'peer_ip': self.peer_ip,
                'peer_port': self.peer_port,
                'peer': self.peer,
                'client': self.client,
                'server': self.server,
                'alias': self.alias}

    def initialize(self, sock, peer):
        self.peer_ip = peer[0]
        self.peer_port = peer[1]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.own = ':'.join(str(prop) for prop in sock)
        self.sock = sock
        try:
            self.alias = self.check_other(self.peer_ip)
            self.configure_context()
            return True
        except MessageFromNotAuthorizedHost:
            self.close_connection()
            return False


class BaseClientProtocol(BaseSenderProtocol, NetworkProtocolMixin, ABC):

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


@dataclass
class BaseServerProtocol(BaseReceiverProtocol, NetworkProtocolMixin, ABC):
    logger: Logger = 'sender'
    allowed_senders: List[IPvAnyNetwork] = field(default_factory=())

    @property
    def client(self) -> str:
        if self.alias:
            return f"{self.alias}({self.peer})"
        return self.peer

    @property
    def server(self) -> str:
        return self.sock

    def raise_message_from_not_authorized_host(self, sender):
        msg = f"Received message from unauthorized host {sender}"
        self.logger.error(msg)
        raise MessageFromNotAuthorizedHost(msg)

    def sender_valid(self, other_ip):
        if self.allowed_networks:
            return any(n.supernet_of(other_ip) for n in self.allowed_networks)
        return True

    def check_other(self, other_ip):
        if self.sender_valid(other_ip):
            return super().check_other(other_ip)
        self.raise_message_from_not_authorized_host(other_ip)


class BaseOneWayServerProtocol(BaseServerProtocol, ABC):
    def send(self, msg_encoded):
        raise NotImplementedError(f"Not possible to send messages with {self.name}")


class BaseTwoWayServerProtocol(BaseServerProtocol, ABC):

    def on_task_complete(self, msg_obj, future):
        response = self.process_result(msg_obj, future)
        if response:
            self.send(response)

    def on_data_received(self, buffer, timestamp=None):
        timestamp = timestamp or datetime.now()
        self.manage_buffer(buffer, timestamp)
        try:
            msgs = self.make_messages(buffer, timestamp)
        except Exception as e:
            self.logger.error(e)
            response = self.action.response_on_decode_error(buffer, e)
            if response:
                self.encode_and_send_msg(response)
        else:
            for msg_obj, task in self.action.do_many(msgs):
                if task:
                    task.add_done_callback(partial(self.on_task_complete, msg_obj))

    def encode_exception(self, msg_obj, exc):
        return self.action.response_on_exception(msg_obj, exc)

    def process_result(self, msg_obj, task):
        result, exception = task.result(), task.exception()
        if result:
            return self.encode_msg(result)
        if exception():
            self.logger.error(exception)
            return self.encode_exception(msg_obj, exception)


