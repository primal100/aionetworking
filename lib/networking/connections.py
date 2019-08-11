from __future__ import annotations
import asyncio
import contextvars
from dataclasses import dataclass, field, replace

from .exceptions import MessageFromNotAuthorizedHost

from lib.actions.protocols import OneWaySequentialAction, ParallelAction
from lib.formats.base import BaseMessageObject
from lib.requesters.protocols import RequesterProtocol
from lib.conf.logging import Logger
from lib.conf.types import ConnectionLoggerType

from .network_connections import connections_manager
from .adaptors import ReceiverAdaptor, OneWayReceiverAdaptor, SenderAdaptor
from .protocols import (ConnectionType, ConnectionProtocol, NetworkConnectionMixinProtocol, ConnectionGeneratorProtocol,
                        ReadWriteConnectionProtocol, AdaptorProtocolGetattr, UDPConnectionMixinProtocol, SenderAdaptorGetattr)
from .types import ConnectionGeneratorType,  NetworkConnectionType, AdaptorType, SenderAdaptorType

from typing import Any, AnyStr, Dict, List, NoReturn, Optional, Text, Tuple, Type, TypeVar, Union
from typing_extensions import Protocol


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


def details_to_str(details: Tuple[str, int]):
    return ':'.join([str(s) for s in details])


@dataclass
class ConnectionGenerator(ConnectionGeneratorProtocol):
    connection: NetworkConnectionProtocol
    logger: Logger = Logger('receiver')

    def __call__(self) -> NetworkConnectionType:
        return self.connection.clone(parent_id=id(self))

    def is_owner(self, connection: NetworkConnectionType) -> bool:
        return connection.is_child(id(self))

    async def wait_all_closed(self) -> None:
        await connections_manager.wait_all_connections_closed(id(self))


@dataclass
class UDPConnectionGenerator(asyncio.DatagramProtocol, ConnectionGenerator):
    transport = None
    sock = None

    def __call__(self: ConnectionGeneratorType) -> ConnectionGeneratorType:
        return self

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.logger.manage_error(exc)
        for conn in filter(self.is_owner, connections_manager):
            conn.finish_connection(exc)

    def error_received(self, exc: Optional[Exception]) -> None:
        self.logger.manage_error(exc)

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple[str, int]) -> None:
        conn = connections_manager.get(details_to_str(addr), None)
        if conn:
            conn.on_data_received(data)
        else:
            conn = self.connection.clone()
            conn.initialize_connection(addr, self.sock)
            conn.set_transport(self.transport)
            conn.on_data_received(data)


@dataclass
class BaseConnectionProtocol(AdaptorProtocolGetattr, ConnectionProtocol, Protocol):
    name = ''
    adaptor_cls: Type[AdaptorType] = None
    action: ParallelAction = None
    preaction: OneWaySequentialAction = None
    requester: RequesterProtocol = None
    dataformat: Type[BaseMessageObject] = None
    adaptor: AdaptorType = field(default=None)
    context: Dict[str, Any] = field(default_factory=dict)
    closed: asyncio.Task = field(default=None, init=False)
    logger: Logger = Logger('receiver')
    parent_id: int = None
    timeout: Union[int, float] = 5

    def __getattr__(self, item):
        if self.adaptor:
            return getattr(self.adaptor, item)

    def _update_context(self) -> None:
        self.context['protocol_name'] = self.name

    def start_adaptor(self) -> None:
        self._update_context()
        self._set_adaptor()
        connections_manager.add_connection(self)
        self.logger.log_num_connections('opened', self.parent_id)

    def _set_adaptor(self) -> None:
        kwargs = {
            'logger': self._get_connection_logger(),
            'context': self.context,
            'dataformat': self.dataformat,
            'preaction': self.preaction,
            'send': self.send
        }
        if self.adaptor_cls.is_receiver:
            self.adaptor = self._get_receiver_adaptor(**kwargs)
        else:
            self.adaptor = self._get_sender_adaptor(**kwargs)

    def _get_receiver_adaptor(self, **kwargs) -> AdaptorType:
        return self.adaptor_cls(action=self.action, **kwargs)

    def _get_sender_adaptor(self, **kwargs) -> SenderAdaptorType:
        return self.adaptor_cls(requester=self.requester, **kwargs)

    def clone(self: ConnectionType, **kwargs) -> ConnectionType:
        return replace(self, **kwargs)

    def is_child(self, parent_id: int) -> bool:
        return parent_id == self.parent_id

    def _get_connection_logger(self) -> ConnectionLoggerType:
        return self.logger.get_connection_logger(is_receiver=self.adaptor_cls.is_receiver, extra=self.context)

    def _delete_connection(self) -> None:
        connections_manager.remove_connection(self)
        self.logger.log_num_connections('closed', self.parent_id)

    async def _close(self, exc: Optional[BaseException]) -> None:
        try:
            await asyncio.wait_for(self.adaptor.close(exc), timeout=self.timeout)
        finally:
            self._delete_connection()

    def finish_connection(self, exc: Optional[BaseException]) -> None:
        self.closed = asyncio.create_task(self._close(exc))

    async def close_wait(self):
        if not self.closed:
            self.finish_connection(None)
        await self.closed


TransportType = TypeVar('TransportType', bound=asyncio.BaseTransport)


@dataclass
class NetworkConnectionProtocol(BaseConnectionProtocol, NetworkConnectionMixinProtocol, Protocol):
    sock = ('', 0)
    peer = ('', 0)
    peer_str = ''
    sock_str = ''
    alias = ''
    transport: TransportType = None

    aliases: dict = field(default_factory=dict)
    #allowed_senders: List[IPvAnyNetwork] = field(default_factory=tuple)

    def _raise_message_from_not_authorized_host(self, peer: Tuple[str, int]) -> NoReturn:
        msg = f"Received message from unauthorized host {self.details_to_str(peer)}"
        self.logger.error(msg)
        raise MessageFromNotAuthorizedHost(msg)

    def _sender_valid(self, other_ip):
        #if self.allowed_senders:
        #    return any(n.supernet_of(other_ip) for n in self.allowed_senders)
        return True

    def _get_alias(self, peer: Tuple[str, int]) -> str:
        host = peer[0]
        alias = self.aliases.get(host, host)
        if alias != host:
            self.logger.debug('Alias found for %s: %s', host, alias)
        return alias

    def _check_peer(self, peer: Tuple[str, int]) -> str:
        if self._sender_valid(peer):
            return self._get_alias(peer)
        self._raise_message_from_not_authorized_host(peer)

    def _update_context(self) -> None:
        super()._update_context()
        self.context.update({
            'peer': self.peer_str,
            'host': self.peer[0],
            'port': self.peer[1],
            'sock': self.sock_str,
            'alias': self.alias
        })
        if self.alias and self.alias not in self.peer_str:
            self.context['peer'] = f"{self.alias}({self.peer_str})"

    def initialize_connection(self, peer: Tuple[str, int], sock:  Tuple[str, int], ) -> bool:
        self.peer = peer
        self.sock = sock
        self.peer_str = details_to_str(peer)
        self.sock_str = details_to_str(sock)
        try:
            self.alias = self._check_peer(self.peer)
            self.start_adaptor()
            return True
        except MessageFromNotAuthorizedHost as exc:
            self.finish_connection(exc)
            return False


@dataclass
class BaseStreamConnection(asyncio.Protocol, NetworkConnectionProtocol):
    transport: asyncio.ReadTransport = None

    def connection_made(self, transport: asyncio.ReadTransport) -> None:
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        self.initialize_connection(peer, sock)

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.transport.close()
        self.write_transport.close()
        self.finish_connection(exc)

    def data_received(self, data: AnyStr) -> None:
        self.adaptor.on_data_received(data)

    def send(self, msg: AnyStr) -> None:
        self.write_transport.write(msg)


class BaseUDPConnection(NetworkConnectionProtocol, UDPConnectionMixinProtocol):

    def set_transport(self, transport: asyncio.DatagramTransport):
        self.transport = transport

    def send(self, msg: AnyStr) -> None:
        self.transport.sendto(msg, self.peer)


@dataclass
class OneWayTCPServerConnection(BaseStreamConnection):
    name = 'TCP Server'
    adaptor_cls: Type[AdaptorType] = OneWayReceiverAdaptor
    action: OneWaySequentialAction = None


@dataclass
class TCPServerConnection(BaseStreamConnection):
    name = 'TCP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor


@dataclass
class TCPClientConnection(BaseStreamConnection, SenderAdaptorGetattr):
    name = 'TCP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor


@dataclass
class OneWayUDPServerConnection(BaseUDPConnection):
    name = 'UDP Server'
    adaptor_cls: Type[AdaptorType] = OneWayReceiverAdaptor
    action: OneWaySequentialAction = None


@dataclass
class UDPServerConnection(BaseUDPConnection):
    name = 'UDP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor


@dataclass
class UDPClientConnection(BaseUDPConnection, SenderAdaptorGetattr):
    name = 'UDP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor
