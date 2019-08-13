from __future__ import annotations
import asyncio
import contextvars
from dataclasses import dataclass, field, replace

from .exceptions import MessageFromNotAuthorizedHost

from lib.actions.protocols import OneWaySequentialAction, ParallelAction
from lib.formats.base import BaseMessageObject
from lib.requesters.types import RequesterType
from lib.conf.logging import Logger
from lib.conf.types import ConnectionLoggerType
from lib.utils import addr_tuple_to_str

from .connections_manager import connections_manager
from .adaptors import ReceiverAdaptor, OneWayReceiverAdaptor, SenderAdaptor
from .protocols import (ConnectionType, ConnectionProtocol, NetworkConnectionMixinProtocol, ProtocolFactoryProtocol,
                        AdaptorProtocolGetattr, UDPConnectionMixinProtocol, SenderAdaptorGetattr)
from .types import ProtocolFactoryType,  NetworkConnectionType, AdaptorType, SenderAdaptorType

from typing import Any, AnyStr, Dict, NoReturn, Optional, Text, Tuple, Type, TypeVar, Union
from lib.compatibility import Protocol


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


def details_to_str(details: Tuple[str, int]):
    return ':'.join([str(s) for s in details])


@dataclass
class ProtocolFactory(ProtocolFactoryProtocol):
    connection: NetworkConnectionProtocol
    logger: Logger = Logger('receiver')

    def __call__(self) -> NetworkConnectionType:
        return self.connection.clone(parent_id=id(self))

    def set_logger(self, logger: Logger) -> None:
        self.logger = logger
        self.connection.set_logger(logger)

    def is_owner(self, connection: NetworkConnectionType) -> bool:
        return connection.is_child(id(self))

    async def wait_num_has_connected(self, num: int) -> None:
        await connections_manager.wait_num_has_connected(id(self), num)

    async def wait_all_messages_processed(self) -> None:
        await connections_manager.wait_all_messages_processed(id(self))

    async def wait_all_closed(self) -> None:
        await connections_manager.wait_all_connections_closed(id(self))


@dataclass
class UDPProtocolFactory(asyncio.DatagramProtocol, ProtocolFactory):
    transport = None
    sock = None

    def __call__(self: ProtocolFactoryType) -> ProtocolFactoryType:
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
            conn.initialize_connection(self.transport, addr)
            conn.on_data_received(data)


@dataclass
class BaseConnectionProtocol(AdaptorProtocolGetattr, ConnectionProtocol, Protocol):
    name = ''
    store_connections = False
    adaptor_cls: Type[AdaptorType] = None
    action: ParallelAction = None
    preaction: OneWaySequentialAction = None
    requester: RequesterType = None
    dataformat: Type[BaseMessageObject] = None
    adaptor: AdaptorType = field(default=None)
    context: Dict[str, Any] = field(default_factory=dict)
    connected: asyncio.Event = field(default_factory=asyncio.Event, init=False, compare=False)
    closed: asyncio.Task = field(default=None, init=False, compare=False)
    logger: Logger = Logger('receiver')
    parent_id: int = None
    timeout: Union[int, float] = 5

    def __getattr__(self, item):
        if self.adaptor:
            return getattr(self.adaptor, item)

    def set_logger(self, logger: Logger) -> None:
        self.logger = logger

    def _initial_context(self) -> None:
        self.context['protocol_name'] = self.name

    def _start_adaptor(self) -> None:
        self._set_adaptor()
        if self.store_connections:
            connections_manager.add_connection(self)
            self.logger.log_num_connections('opened', self.parent_id)

    @property
    def peer(self) -> str:
        return self.context.get('peer')

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
        if self.store_connections:
            connections_manager.remove_connection(self)
            self.logger.log_num_connections('closed', self.parent_id)

    async def _close(self, exc: Optional[BaseException]) -> None:
        try:
            if self.adaptor:
                await asyncio.wait_for(self.adaptor.close_actions(exc), timeout=self.timeout)
        finally:
            self._delete_connection()

    def finish_connection(self, exc: Optional[BaseException]) -> None:
        self.connected.clear()
        self.closed = asyncio.create_task(self._close(exc))

    async def close_wait(self):
        if not self.closed:
            self.finish_connection(None)
        await self.closed

    async def wait_connected(self) -> None:
        await self.connected.wait()

    def is_connected(self) -> bool:
        return self.connected.is_set()


TransportType = TypeVar('TransportType', bound=asyncio.BaseTransport)


@dataclass
class NetworkConnectionProtocol(BaseConnectionProtocol, NetworkConnectionMixinProtocol, Protocol):
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

    def _get_alias(self, host: str) -> str:
        alias = self.aliases.get(host, host)
        if alias != host:
            self.logger.debug('Alias found for %s: %s', host, alias)
        return alias

    def _check_peer(self) -> None:
        peer = self.context['peer']
        host = self.context['host']
        if self._sender_valid(host):
            alias = self._get_alias(host)
            self.context['alias'] = alias
            if alias and alias not in peer:
                self.context['peer'] = f"{self.alias}({peer})"
        else:
            self._raise_message_from_not_authorized_host(peer)

    def initialize_connection(self, transport: asyncio.BaseTransport, peer: Tuple[str, int] = None) -> bool:
        check_sender = self._update_context(transport, peer)
        try:
            if check_sender:
                self._check_peer()
            self._start_adaptor()
            self.connected.set()
            return True
        except MessageFromNotAuthorizedHost as exc:
            self.finish_connection(exc)
            return False

    def _update_context(self, transport: asyncio.BaseTransport, peer: Tuple[str, int] = None) -> bool:
        self._initial_context()
        sockname = transport.get_extra_info('sockname')
        if sockname:
            if peer:
                #UDP server transport
                pass
            else:
                peer = transport.get_extra_info('peername')
                #TCP Stream transport
            if peer:
                #UDP or TCP INET transport
                self.context['peer'] = addr_tuple_to_str(peer)
                self.context['sock'] = addr_tuple_to_str(sockname)
                self.context['host'], self.context['port'] = peer
                return True
            else:
                #AF_UNIX server transport
                fd = transport.get_extra_info('socket').fileno()
                self.context['fd'] = fd
                self.context['addr'] = sockname
                self.context['peer'] = f"{sockname}.{fd}"
                return False
        elif peer:
            #AF_UNIX client transport
            fd = transport.get_extra_info('socket').fileno()
            self.context['fd'] = fd
            self.context['addr'] = peer
            self.context['peer'] = f"{peer}.{fd}"
            self.context['alias'] = str(fd)
            return False
        else:
            #Pipe Duplex transport
            addr = transport.get_extra_info('addr')
            handle = transport.get_extra_info('pipe').handle
            self.context['addr'] = addr
            self.context['handle'] = handle
            self.context['peer'] = f"{addr}.{handle}"
            self.context['alias'] = str(handle)
            return False


@dataclass
class BaseStreamConnection(asyncio.Protocol, NetworkConnectionProtocol):
    transport: asyncio.Transport = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.initialize_connection(transport)

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        if not self.transport.is_closing():
            self.transport.close()
        self.finish_connection(exc)

    def data_received(self, data: AnyStr) -> None:
        self.adaptor.on_data_received(data)

    def send(self, msg: AnyStr) -> None:
        self.transport.write(msg)


@dataclass
class BaseUDPConnection(NetworkConnectionProtocol, UDPConnectionMixinProtocol):
    _peer: Tuple[str, int] = field(default=None, init=False)

    def initialize_connection(self, transport: asyncio.BaseTransport, peer: Tuple[str, int] = None):
        self.transport = transport
        self._peer = peer
        super().initialize_connection(transport, peer=peer)

    def send(self, msg: AnyStr) -> None:
        self.transport.sendto(msg, self._peer)


@dataclass
class OneWayTCPServerConnection(BaseStreamConnection):
    name = 'TCP Server'
    adaptor_cls: Type[AdaptorType] = OneWayReceiverAdaptor
    action: OneWaySequentialAction = None
    store_connections = True


@dataclass
class TCPServerConnection(BaseStreamConnection):
    name = 'TCP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor
    store_connections = True


@dataclass
class TCPClientConnection(BaseStreamConnection, SenderAdaptorGetattr):
    name = 'TCP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor


@dataclass
class OneWayUDPServerConnection(BaseUDPConnection):
    name = 'UDP Server'
    adaptor_cls: Type[AdaptorType] = OneWayReceiverAdaptor
    action: OneWaySequentialAction = None
    store_connections = True


@dataclass
class UDPServerConnection(BaseUDPConnection):
    name = 'UDP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor
    store_connections = True


@dataclass
class UDPClientConnection(BaseUDPConnection, SenderAdaptorGetattr):
    name = 'UDP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor
