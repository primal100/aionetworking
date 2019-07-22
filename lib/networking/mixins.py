from abc import ABC
import asyncio
from dataclasses import dataclass, field

from .exceptions import MessageFromNotAuthorizedHost
from lib.utils_logging import p
from .asyncio_protocols import BaseReceiverProtocol, BaseSenderProtocol, MessageObjectType, ProtocolType, msg_obj_cv

from socket import socket
from typing import Iterator, Tuple, AnyStr, ClassVar, MutableMapping


@dataclass
class NetworkProtocolMixin(ABC):
    connections: ClassVar[MutableMapping[str, ProtocolType]] = {}
    aliases: dict = field(default_factory=dict)
    sock = (None, None)
    alias = ''
    peer = None
    transport = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.new_connection()
            self.connections[''.join(peer)] = self
            self.logger.debug('Connection opened. There %s now %s.', p.plural_verb('is', p.num(len(self.connections))),
                              p.no('active connection'))

    def _close_connection(self) -> None:
        pass

    def connection_lost(self, exc) -> None:
        self.logger.connection_finished(exc)
        self._close_connection()
        self.connections.pop(self.peer, None)

    def _get_alias(self, peer: Tuple[str, int]) -> str:
        host = peer[0]
        alias = self.aliases.get(host, host)
        if alias != host:
            self.parent_logger.debug('Alias found for %s: %s', host, alias)
        return alias

    def _check_peer(self, peer: Tuple[str, int]) -> str:
        return self._get_alias(peer)

    def update_context_with_connection_details(self):
        self.context['peer'] = self.peer
        self.context['sock'] = self.sock
        self.context['alias'] = self.alias

    def initialize(self, sock: socket, peer: Tuple[str, int]) -> bool:
        self.peer = peer
        self.sock = sock
        try:
            self.alias = self._check_peer(self.peer[0])
            self.update_context_with_connection_details()
            self._configure_context()
            return True
        except MessageFromNotAuthorizedHost:
            self._close_connection()
            return False


class BaseClientProtocol(BaseSenderProtocol, NetworkProtocolMixin, ABC):
    pass


@dataclass
class BaseServerProtocol(BaseReceiverProtocol, NetworkProtocolMixin, ABC):
    #allowed_senders: List[IPvAnyNetwork] = field(default_factory=tuple)

    def _raise_message_from_not_authorized_host(self, sender):
        msg = f"Received message from unauthorized host {sender}"
        self.logger.error(msg)
        raise MessageFromNotAuthorizedHost(msg)

    def _sender_valid(self, other_ip):
        #if self.allowed_senders:
        #    return any(n.supernet_of(other_ip) for n in self.allowed_senders)
        return True

    def _check_peer(self, other_ip):
        if self._sender_valid(other_ip):
            return super()._check_peer(other_ip)
        self._raise_message_from_not_authorized_host(other_ip)


class BaseTwoWayServerProtocol(BaseServerProtocol, ABC):

    def encode_exception(self, msg_obj: MessageObjectType, exc: BaseException) -> MessageObjectType:
        return self.action.response_on_exception(msg_obj, exc)

    def process_result(self, future: asyncio.Future) -> MessageObjectType:
        result, exception = future.result(), future.exception()
        if result:
            return self.encode_msg(result)
        if exception:
            self.logger.error(exception)
            return self.encode_exception(msg_obj_cv, exception)

    def on_task_complete(self, future: asyncio.Future) -> None:
        response = self.process_result(future)
        if response:
            self.send(response)
        self._scheduler.task_done()

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        try:
            for msg in msgs:
                msg_obj_cv.set(msg)
                self._scheduler.create_task(self.action.do_one(msg), callback=self.on_task_complete)
        except Exception as e:
            self.logger.error(e)
            response = self.action.response_on_decode_error(buffer, e)
            if response:
                self.encode_and_send_msg(response)
