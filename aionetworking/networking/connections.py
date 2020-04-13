import asyncio
from dataclasses import dataclass, field
from pathlib import Path
import datetime
from functools import partial
import socket

from .exceptions import MessageFromNotAuthorizedHost

from aionetworking.compatibility import create_task, set_task_name
from aionetworking.context import context_cv
from aionetworking.logging.loggers import connection_logger_cv, get_logger_receiver
from aionetworking.types.logging import LoggerType, ConnectionLoggerType
from aionetworking.types.networking import AFINETContext, AFUNIXContext, NamedPipeContext
from aionetworking.utils import addr_tuple_to_str, dataclass_getstate, dataclass_setstate, IPNetwork, supernet_of, hostname_or_ip
from aionetworking.futures.value_waiters import StatusWaiter

from .connections_manager import connections_manager
from .adaptors import ReceiverAdaptor, SenderAdaptor
from .protocols import (
    ConnectionDataclassProtocol, AdaptorProtocolGetattr, UDPConnectionMixinProtocol, SenderAdaptorGetattr)
from .transports import TransportType, DatagramTransportWrapper
from aionetworking.types.networking import AdaptorType, SenderAdaptorType

from typing import NoReturn, Optional, Tuple, Type, Dict, Any, Sequence, Callable, Awaitable, List
from aionetworking.compatibility import Protocol


AsyncCallable = Callable[[int], Awaitable[None]]


@dataclass
class BaseConnectionProtocol(AdaptorProtocolGetattr, ConnectionDataclassProtocol, Protocol):
    _connected: asyncio.Future = field(default_factory=asyncio.Future, init=False, compare=False)
    _closing: asyncio.Future = field(default_factory=asyncio.Future, init=False, compare=False)
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)
    context: Dict[str, Any] = field(default_factory=context_cv.get, metadata={'pickle': True})
    codec_config: Dict[str, Any] = field(default_factory=dict, metadata={'pickle': True})
    logger: LoggerType = field(default_factory=get_logger_receiver, metadata={'pickle': True})

    def __post_init__(self):
        names = self.parent_name.split(' ')
        self.context['protocol_name'] = f'{names[0]} {names[1]}'

    def __getattr__(self, item):
        if self._adaptor:
            try:
                return getattr(self._adaptor, item)
            except AttributeError:
                raise AttributeError(f"Neither connection nor adaptor have attribute {item}")
        raise AttributeError(f"Connection does not have attribute {item}, and adaptor has not been configured yet")

    def _start_adaptor(self) -> None:
        self._set_adaptor()
        num = connections_manager.add_connection(self)
        self.logger.log_num_connections('opened', num)

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    @staticmethod
    def get_peername(peer_prefix: str, peer: str, own: str) -> str:
        return f"{peer_prefix}_{own}_{peer}"

    @property
    def peer(self) -> str:
        return self.get_peername(self.peer_prefix, self.context.get('peer'), self.context.get('own'))

    def _set_adaptor(self) -> None:
        connection_logger_cv.set(self._get_connection_logger())
        kwargs = {
            'context': self.context,
            'dataformat': self.dataformat,
            'preaction': self.preaction,
            'send': self.send,
            'codec_config': self.codec_config
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
        connections_manager.remove_connection(self)

    async def _close(self, exc: Optional[BaseException]) -> None:
        try:
            if self._adaptor:
                await asyncio.wait_for(self._adaptor.close(exc), timeout=self.timeout)
        finally:
            if self._adaptor:
                num = connections_manager.decrement(self)
                self.logger.log_num_connections('closed', num)
            self._status.set_stopped()

    def finish_connection(self, exc: Optional[BaseException]) -> None:
        if self._adaptor:
            self._adaptor.logger.info('Finishing connection')
            self._delete_connection()
        self._status.set_stopping()
        close_task = create_task(self._close(exc))
        set_task_name(close_task, f"Close:{self.peer}")

    def close(self, immediate: bool = False):
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
        self.last_msg = datetime.datetime.now()
        self._adaptor.on_data_received(data, timestamp=self.last_msg)


@dataclass
class NetworkConnectionProtocol(BaseConnectionProtocol, Protocol):
    transport: asyncio.BaseTransport = field(default=None, init=False)
    pause_reading_on_buffer_size: int = None
    allowed_senders: Sequence[IPNetwork] = field(default_factory=tuple)
    hostname_lookup: bool = False
    connection_lost_tasks: List[AsyncCallable] = field(default_factory=list)
    _unprocessed_data: int = field(default=0, init=False, repr=False)

    def _raise_message_from_not_authorized_host(self, host: str) -> NoReturn:
        msg = f"Received message from unauthorized host {host}"
        self.logger.error(msg)
        raise MessageFromNotAuthorizedHost(msg)

    def _sender_valid(self, peer_ip, peer_hostname):
        if self.allowed_senders:
            return supernet_of(peer_ip, peer_hostname, self.allowed_senders)
        return True

    def _check_peer(self) -> None:
        if not self._sender_valid(self.context['address'], self.context['host']):
            self._raise_message_from_not_authorized_host(self.context['host'])

    def close(self, immediate: bool = False):
        if not self.transport.is_closing():
            self.transport.close()

    def log_context(self):
        self.logger.info(self.context)

    def initialize_connection(self, transport: TransportType, **extra_context) -> bool:
        self._status.set_starting()
        self._update_context(transport)
        self.context.update(extra_context)
        try:
            if self.context.get('host'):
                self._check_peer()
            self.last_msg = datetime.datetime.now()
            self._start_adaptor()
            self._status.set_started()
            return True
        except MessageFromNotAuthorizedHost:
            self.close(immediate=True)
            return False

    def add_connection_lost_task(self, async_function: AsyncCallable):
        self.connection_lost_tasks.append(async_function)

    def run_connection_lost_tasks(self) -> None:
        if self.connection_lost_tasks:
            connection_lost_tasks = [t() for t in self.connection_lost_tasks]
            create_task(asyncio.wait(connection_lost_tasks))

    def eof_received(self) -> bool:
        return False

    def _update_context(self, transport: TransportType) -> None:
        _socket = transport.get_extra_info('socket', None)
        if _socket and hasattr(socket, 'AF_UNIX') and _socket.family == socket.AF_UNIX:
            # AF_UNIX server transport
            sockname: str = transport.get_extra_info('sockname') or transport.get_extra_info('peername')
            fd: int = _socket.fileno()
            self.context: AFUNIXContext = {
                'protocol_name': self.context['protocol_name'],
                'address': Path(sockname).name,
                'peer': str(fd) if self.adaptor_cls.is_receiver else sockname,
                'own': sockname if self.adaptor_cls.is_receiver else str(fd),
                'alias': f'{sockname}.{fd}',
                'server': sockname,
                'client': str(fd),
                'fd': fd,
            }
        elif transport.get_extra_info('pipe', None):
            # Windows Named Pipe Transport
            addr: str = transport.get_extra_info('addr')
            handle: int = transport.get_extra_info('pipe').handle
            peer: str = str(handle) if self.adaptor_cls.is_receiver else addr
            self.context: NamedPipeContext = {
                'protocol_name': self.context['protocol_name'],
                'address': Path(addr).name,
                'server': addr,
                'handle': handle,
                'client': str(handle),
                'own': addr if self.adaptor_cls.is_receiver else str(handle),
                'peer': peer,
                'alias': f'{addr}.{handle}'
            }
        else:
            # INET/INET6 transport
            peer: Tuple[str, int] = transport.get_extra_info('peername')[0:2]
            sockname: Tuple[str, int] = transport.get_extra_info('sockname')[0:2]
            peer_str = addr_tuple_to_str(peer)
            sock_str = addr_tuple_to_str(sockname)
            if self.hostname_lookup:
                host = hostname_or_ip(peer[0])
            else:
                host = peer[0]
            self.context: AFINETContext = {
                'protocol_name': self.context['protocol_name'],
                'peer': peer_str,
                'own': sock_str,
                'address': peer[0],
                'port': peer[1],
                'host': host,
                'alias': '',
                'server': sock_str if self.adaptor_cls.is_receiver else peer_str,
                'client': peer_str if self.adaptor_cls.is_receiver else sock_str
            }
            if self.context['host'] not in self.context['address']:
                self.context['alias'] = f"{self.context['host']}({self.context['peer']})"
            else:
                self.context['alias'] = self.context['host']
        self.log_context()
        cipher = transport.get_extra_info('cipher', default=None)
        if cipher:
            self.logger.info(f"Cipher: {cipher}', 'Compression': {transport.get_extra_info('compression')}")
            self.logger.debug(transport.get_extra_info('peercert'))

    def send(self, msg: bytes) -> None:
        self.transport.write(msg)
        self.last_msg = datetime.datetime.now()


@dataclass
class BaseStreamConnection(NetworkConnectionProtocol, Protocol):
    transport: asyncio.Transport = field(default=None, init=False, repr=False, compare=False)

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.initialize_connection(transport)

    def _close_transport(self, task: asyncio.Future):
        self.transport.close()

    def close(self, immediate: bool = False):
        if not self.transport.is_closing():
            if immediate:
                self.transport.abort()
            elif self._adaptor:
                task = create_task(self.wait_current_tasks())
                task.add_done_callback(self._close_transport)
            else:
                self.transport.close()

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.close()
        self.run_connection_lost_tasks()
        self.finish_connection(exc)

    def _resume_reading(self, datalen: int, fut: asyncio.Future):
        self._unprocessed_data -= datalen
        if (self.pause_reading_on_buffer_size is not None and not self.transport.is_reading() and
                not self.transport.is_closing()):
            if self.pause_reading_on_buffer_size >= self._unprocessed_data:
                self.transport.resume_reading()
                self._adaptor.logger.info('Reading resumed')
        fut.result()

    def data_received(self, data: bytes) -> None:
        self.last_msg = datetime.datetime.now()
        self._unprocessed_data += len(data)
        if self.pause_reading_on_buffer_size is not None:
            if self.pause_reading_on_buffer_size <= len(data):
                self.transport.pause_reading()
                self.logger.info('Reading Paused')
        task = self._adaptor.on_data_received(data, timestamp=self.last_msg)
        task.add_done_callback(partial(self._resume_reading, len(data)))


@dataclass
class BaseUDPConnection(NetworkConnectionProtocol, UDPConnectionMixinProtocol):
    _peer: Tuple[str, int] = field(default=None, init=False)
    transport: DatagramTransportWrapper = field(default=None, init=False, repr=False, compare=False)

    def connection_made(self, transport: DatagramTransportWrapper) -> bool:
        self.transport = transport
        return self.initialize_connection(transport)

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.run_connection_lost_tasks()
        self.finish_connection(exc)


@dataclass
class TCPServerConnection(BaseStreamConnection):
    name = 'TCP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor


@dataclass
class TCPClientConnection(BaseStreamConnection, SenderAdaptorGetattr, asyncio.Protocol):
    name = 'TCP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor


@dataclass
class UDPServerConnection(BaseUDPConnection):
    name = 'UDP Server'
    adaptor_cls: Type[AdaptorType] = ReceiverAdaptor


@dataclass
class UDPClientConnection(BaseUDPConnection, SenderAdaptorGetattr):
    name = 'UDP Client'
    adaptor_cls: Type[AdaptorType] = SenderAdaptor

