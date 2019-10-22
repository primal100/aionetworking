from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
import socket

from .exceptions import MessageFromNotAuthorizedHost

from lib.compatibility import set_task_name
from lib.conf.context import context_cv
from lib.conf.logging import Logger, logger_cv, connection_logger_cv
from lib.conf.types import ConnectionLoggerType
from lib.utils import addr_tuple_to_str, dataclass_getstate, dataclass_setstate
from lib.wrappers.value_waiters import StatusWaiter

from .connections_manager import connections_manager
from .adaptors import ReceiverAdaptor, SenderAdaptor
from .protocols import (
    ConnectionDataclassProtocol, AdaptorProtocolGetattr, UDPConnectionMixinProtocol, SenderAdaptorGetattr)
from .transports import TransportType, DatagramTransportWrapper
from .types import AdaptorType, SenderAdaptorType

from typing import NoReturn, Optional, Tuple, Type, Dict, Any
from lib.compatibility import Protocol


@dataclass
class BaseConnectionProtocol(AdaptorProtocolGetattr, ConnectionDataclassProtocol, Protocol):
    _connected: asyncio.Future = field(default_factory=asyncio.Future, init=False, compare=False)
    _closing: asyncio.Future = field(default_factory=asyncio.Future, init=False, compare=False)
    _close_task: asyncio.Task = field(default=None, init=False, compare=False)
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)
    context: Dict[str, Any] = field(default_factory=context_cv.get, metadata={'pickle': True})
    logger: Logger = field(default_factory=logger_cv.get, metadata={'pickle': True})

    def __post_init__(self):
        self.context['protocol_name'] = self.name

    def __getattr__(self, item):
        if self._adaptor:
            try:
                return getattr(self._adaptor, item)
            except AttributeError:
                raise AttributeError(f"Neither connection nor adaptor have attribute {item}")
        raise AttributeError(f"Connection does not have attribute {item}, and adaptor has not been configured yet")

    def _start_adaptor(self) -> None:
        self._set_adaptor()
        if self.store_connections:
            num = connections_manager.add_connection(self)
            self.logger.log_num_connections('opened', num)

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    @staticmethod
    def get_peername(peer_prefix: str, peer: str) -> str:
        return f"{peer_prefix}_{peer}"

    @property
    def peer(self) -> str:
        return self.get_peername(self.peer_prefix, self.context.get('peer'))

    def _set_adaptor(self) -> None:
        connection_logger_cv.set(self._get_connection_logger())
        kwargs = {
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
                await asyncio.wait_for(self._adaptor.close(exc), timeout=self.timeout)
        finally:
            self._status.set_stopped()

    def finish_connection(self, exc: Optional[BaseException]) -> None:
        self._adaptor.logger.info('Finishing connection')
        self._status.set_stopping()
        self._close_task = asyncio.create_task(self._close(exc))
        set_task_name(self._close_task, f"Close:{self.peer}")
        self._delete_connection()

    def close(self):
        self.finish_connection(None)

    async def wait_closed(self) -> None:
        await self._status.wait_stopped()

    async def wait_connected(self) -> None:
        await self._status.wait_started()

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped()

    def is_connected(self) -> bool:
        return self._status.is_started()

    def data_received(self, data: bytes) -> None:
        self._adaptor.on_data_received(data)


@dataclass
class NetworkConnectionProtocol(BaseConnectionProtocol, Protocol):
    transport: asyncio.BaseTransport = field(default=None, init=False)
    aliases: dict = field(default_factory=dict)
    pause_reading_on_buffer_size: int = None
    _unprocessed_data: int = field(default=0, init=False)
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

    def close(self):
        if not self.transport.is_closing():
            self.transport.close()

    def log_context(self):
        self.logger.info(self.context)

    def initialize_connection(self, transport: TransportType, **extra_context) -> bool:
        self._status.set_starting()
        self.context.update(extra_context)
        self._update_context(transport)
        try:
            if self.context.get('host'):
                self._check_peer()
            self._start_adaptor()
            self.log_context()
            self._status.set_started()
            return True
        except MessageFromNotAuthorizedHost as exc:
            self.finish_connection(exc)
            return False

    def eof_received(self) -> bool:
        return False

    def _update_context(self, transport: TransportType) -> None:
        _socket = transport.get_extra_info('socket', None)
        if _socket and hasattr(socket, 'AF_UNIX') and _socket.family == socket.AF_UNIX:
            # AF_UNIX server transport
            sockname = transport.get_extra_info('sockname', None)
            fd = _socket.fileno()
            self.context['fd'] = fd
            if self.adaptor_cls.is_receiver:
                self.context['peer'] = str(fd)
                self.context['addr'] = sockname
                self.context['alias'] = self.context['peer']
                self.context['server'] = sockname
                self.context['client'] = self.context['fd']
            else:
                self.context['fd'] = fd
                self.context['addr'] = transport.get_extra_info('peername')
                self.context['peer'] = self.context['addr']
                self.context['alias'] = self.context['peer']
                self.context['server'] = self.context['addr']
                self.context['client'] = self.context['fd']
            return
        if transport.get_extra_info('pipe', None):
            # Windows Named Pipe Transport
            addr = transport.get_extra_info('addr')
            handle = transport.get_extra_info('pipe').handle
            self.context['addr'] = addr
            self.context['handle'] = handle
            self.context['alias'] = str(handle)
            self.context['server'] = self.context['addr']
            self.context['client'] = self.context['handle']
            self.context['peer'] = self.context['client'] if self.adaptor_cls.is_receiver else self.context['server']
            return
        # INET/INET6 transport
        peer = transport.get_extra_info('peername')
        sockname = transport.get_extra_info('sockname', None)
        self.context['peer'] = addr_tuple_to_str(peer)
        self.context['sock'] = addr_tuple_to_str(sockname)
        self.context['host'], self.context['port'] = peer
        self.context['server'] = self.context['sock'] if self.adaptor_cls.is_receiver else self.context['peer']
        self.context['client'] = self.context['peer'] if self.adaptor_cls.is_receiver else self.context['sock']
        return


@dataclass
class BaseStreamConnection(NetworkConnectionProtocol, Protocol):
    transport: asyncio.Transport = field(default=None, init=False, repr=False, compare=False)

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.initialize_connection(transport)

    def close(self):
        if not self.transport.is_closing():
            self.transport.close()

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.close()
        self.finish_connection(exc)

    def _resume_reading(self, fut: asyncio.Future):
        self._unprocessed_data -= fut.result()
        if (self.pause_reading_on_buffer_size is not None and not self.transport.is_reading() and
                not self.transport.is_closing()):
                if self.pause_reading_on_buffer_size >= self._unprocessed_data:
                    self.transport.resume_reading()
                    self._adaptor.logger.info('Reading resumed')

    def data_received(self, data: bytes) -> None:
        self._unprocessed_data += len(data)
        if self.pause_reading_on_buffer_size is not None:
            if self.pause_reading_on_buffer_size <= len(data):
                self.transport.pause_reading()
                self.logger.info('Reading Paused')
        task = self._adaptor.on_data_received(data)
        task.add_done_callback(self._resume_reading)

    def send(self, msg: bytes) -> None:
        self.transport.write(msg)


@dataclass
class BaseUDPConnection(NetworkConnectionProtocol, UDPConnectionMixinProtocol):
    _peer: Tuple[str, int] = field(default=None, init=False)
    transport: DatagramTransportWrapper = field(default=None, init=False, repr=False, compare=False)

    def connection_made(self, transport: DatagramTransportWrapper) -> None:
        self.transport = transport
        self.initialize_connection(transport)

    def send(self, msg: bytes) -> None:
        self.transport.write(msg)

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.close()
        self.finish_connection(exc)


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
    store_connections = True

