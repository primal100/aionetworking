from __future__ import annotations
import asyncio
import contextvars
from dataclasses import dataclass, field

from .exceptions import MessageFromNotAuthorizedHost, ConnectionAlreadyClosedError

from lib.compatibility import singledispatchmethod, set_task_name
from lib.conf.types import ConnectionLoggerType
from lib.utils import addr_tuple_to_str, dataclass_getstate, dataclass_setstate

from .connections_manager import connections_manager
from .adaptors import ReceiverAdaptor, SenderAdaptor
from .protocols import (
    ConnectionDataclassProtocol, AdaptorProtocolGetattr, UDPConnectionMixinProtocol, SenderAdaptorGetattr, TransportType)
from .types import AdaptorType, SenderAdaptorType

from typing import AnyStr, NoReturn, Optional, Tuple, Type
from lib.compatibility import Protocol


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


@dataclass
class BaseConnectionProtocol(AdaptorProtocolGetattr, ConnectionDataclassProtocol, Protocol):
    _connected: asyncio.Future = field(default_factory=asyncio.Future, init=False, compare=False)
    _closing: asyncio.Future = field(default_factory=asyncio.Future, init=False, compare=False)
    _close_task: asyncio.Task = field(default=None, init=False, compare=False)

    def __post_init__(self):
        self.context['protocol_name'] = self.name
        self.context['endpoint'] = self.parent_name

    def __getattr__(self, item):
        if self._adaptor:
            return getattr(self._adaptor, item)

    def _start_adaptor(self) -> None:
        self._set_adaptor()
        if self.store_connections:
            num = connections_manager.add_connection(self)
            self.logger.log_num_connections('opened', num)

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    @property
    def peer(self) -> str:
        return f"{self.peer_prefix}_{self.context.get('peer')}"

    def _set_adaptor(self) -> None:
        kwargs = {
            'logger': self._get_connection_logger(),
            'context': self.context,
            'dataformat': self.dataformat,
            'preaction': self.preaction,
            'send': self.send
        }
        if self.adaptor_cls.is_receiver:
            self._adaptor = self._get_receiver_adaptor(**kwargs)
        else:
            self._adaptor = self._get_sender_adaptor(**kwargs)

    def _get_receiver_adaptor(self, **kwargs) -> AdaptorType:
        return self.adaptor_cls(action=self.action, **kwargs)

    def _get_sender_adaptor(self, **kwargs) -> SenderAdaptorType:
        return self.adaptor_cls(requester=self.requester, **kwargs)

    def is_child(self, parent_name: str) -> bool:
        return parent_name == self.parent_name

    def _get_connection_logger(self) -> ConnectionLoggerType:
        return self.logger.get_connection_logger(extra=self.context)

    def _delete_connection(self) -> None:
        if self.store_connections:
            num = connections_manager.remove_connection(self)
            self.logger.log_num_connections('closed', num)

    async def _close(self, exc: Optional[BaseException]) -> None:
        try:
            if self._adaptor:
                task = asyncio.create_task(self._adaptor.close(exc))
                set_task_name(task, "CloseAdaptor")
                await asyncio.wait_for(task, timeout=self.timeout)
        finally:
            self._delete_connection()

    def finish_connection(self, exc: Optional[BaseException]) -> None:
        if self._connected.done():
            self._connected = asyncio.Future()
        elif exc:
            self._connected.set_exception(exc)
        else:
            self._connected.set_exception(ConnectionAlreadyClosedError())
        self._close_task = asyncio.create_task(self._close(exc))
        set_task_name(self._close_task, f"Close:{self.peer}")
        self._closing.set_result(True)

    def close(self):
        self.finish_connection(None)

    async def close_wait(self):
        if not self._closing.done():
            self.close()
        await self._closing
        await self._close_task

    async def wait_connected(self) -> bool:
        return await self._connected

    def is_connected(self) -> bool:
        return self._connected.done() and self._connected.result()


@dataclass
class NetworkConnectionProtocol(BaseConnectionProtocol, Protocol):
    transport: asyncio.BaseTransport = field(default=None, init=False)
    aliases: dict = field(default_factory=dict)
    #allowed_senders: List[IPvAnyNetwork] = field(default_factory=tuple)

    def _raise_message_from_not_authorized_host(self, host: str) -> NoReturn:
        msg = f"Received message from unauthorized host {host}"
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
            self._raise_message_from_not_authorized_host(host)

    def initialize_connection(self, transport: TransportType, peer: Tuple[str, int] = None) -> bool:
        self._update_context(transport, peer)
        try:
            if self.context.get('host'):
                self._check_peer()
            self._start_adaptor()
            self._connected.set_result(True)
            return True
        except MessageFromNotAuthorizedHost as exc:
            self.finish_connection(exc)
            return False

    @singledispatchmethod
    def _update_context(self, transport: asyncio.Transport, peer: Tuple[str, int] = None):
        sockname = transport.get_extra_info('sockname')
        peer = transport.get_extra_info('peername')
        if peer:
            #TCP INET transport
            self.context['peer'] = addr_tuple_to_str(peer)
            self.context['sock'] = addr_tuple_to_str(sockname)
            self.context['host'], self.context['port'] = peer
            self.context['server'] = self.context['sock'] if self.adaptor_cls.is_receiver else self.context['peer']
            self.context['client'] = self.context['peer'] if self.adaptor_cls.is_receiver else self.context['sock']
        else:
            #AF_UNIX server transport
            fd = transport.get_extra_info('socket').fileno()
            self.context['fd'] = fd
            self.context['peer'] = str(fd)
            self.context['sock'] = sockname
            self.context['alias'] = self.context['peer']
            self.context['server'] = self.context['sock']
            self.context['client'] = self.context['fd']

    @_update_context.register
    def _update_context_udp(self, transport: asyncio.DatagramTransport, peer: Tuple[str, int] = None):
        sockname = transport.get_extra_info('sockname')
        self.context['peer'] = addr_tuple_to_str(peer)
        self.context['sock'] = addr_tuple_to_str(sockname)
        self.context['host'], self.context['port'] = peer
        self.context['server'] = self.context['sock'] if self.adaptor_cls.is_receiver else self.context['peer']
        self.context['client'] = self.context['peer'] if self.adaptor_cls.is_receiver else self.context['sock']

    @_update_context.register
    def _update_context_pipe(self, transport: asyncio.proactor_events._ProactorDuplexPipeTransport, peer: Tuple[str, int] = None):
        addr = transport.get_extra_info('addr')
        handle = transport.get_extra_info('pipe').handle
        self.context['addr'] = addr
        self.context['handle'] = handle
        self.context['peer'] = f"{addr}.{handle}"
        self.context['alias'] = str(handle)
        self.context['server'] = self.context['addr']
        self.context['client'] = self.context['handle']


@dataclass
class BaseStreamConnection(NetworkConnectionProtocol, Protocol):
    transport: asyncio.Transport = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.initialize_connection(transport)

    def close(self):
        if not self.transport.is_closing():
            self.transport.close()

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.finish_connection(exc)

    def data_received(self, data: AnyStr) -> None:
        self._adaptor.on_data_received(data)

    def eof_received(self) -> bool:
        return False

    def send(self, msg: AnyStr) -> None:
        self.transport.write(msg)


@dataclass
class BaseUDPConnection(NetworkConnectionProtocol, UDPConnectionMixinProtocol):
    _peer: Tuple[str, int] = field(default=None, init=False)
    transport: asyncio.DatagramTransport = None

    def initialize_connection(self, transport: asyncio.DatagramTransport, peer: Tuple[str, int] = None):
        self.transport = transport
        self._peer = peer
        super().initialize_connection(transport, peer=peer)

    def send(self, msg: AnyStr) -> None:
        self.transport.sendto(msg, self._peer)


@dataclass
class TCPServerConnection(BaseStreamConnection):
    name = 'TCP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor
    store_connections = True


@dataclass
class TCPClientConnection(BaseStreamConnection, SenderAdaptorGetattr, asyncio.Protocol):
    name = 'TCP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor
    store_connections = False


@dataclass
class UDPServerConnection(BaseUDPConnection):
    name = 'UDP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor
    store_connections = True


@dataclass
class UDPClientConnection(BaseUDPConnection, SenderAdaptorGetattr):
    name = 'UDP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor
    store_connections = False

