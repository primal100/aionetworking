from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
import contextvars

from aionetworking.actions.protocols import ActionProtocol
from aionetworking.conf.context import context_cv
from aionetworking.formats.base import BaseMessageObject
from aionetworking.types.requesters import RequesterType
from aionetworking.conf.logging import Logger, logger_cv
from aionetworking.utils import dataclass_getstate, dataclass_setstate, addr_tuple_to_str, IPNetwork
from .transports import DatagramTransportWrapper


from .connections_manager import connections_manager
from .connections import TCPClientConnection, TCPServerConnection, UDPServerConnection, UDPClientConnection
from .protocols import ProtocolFactoryProtocol
from aionetworking.types.networking import ProtocolFactoryType,  NetworkConnectionType

from typing import Optional, Text, Tuple, Type, Union, Sequence, Dict, Any


@dataclass
class BaseProtocolFactory(ProtocolFactoryProtocol):
    full_name = ''
    peer_prefix = ''
    connection_cls: Type[NetworkConnectionType] = field(default=None, init=False)
    action: ActionProtocol = None
    preaction: ActionProtocol = None
    requester: RequesterType = None
    dataformat: Type[BaseMessageObject] = None
    logger: Logger = Logger('receiver')
    pause_reading_on_buffer_size: int = None
    aliases: Dict[str, str] = field(default_factory=dict)
    allowed_senders: Sequence[IPNetwork] = field(default_factory=tuple)
    codec_config: Dict[str, Any] = field(default_factory=dict, metadata={'pickle': True})
    _context: contextvars.Context = field(default=None, init=False, compare=False, repr=False)

    async def start(self) -> None:
        self._context = contextvars.copy_context()
        self.logger = logger_cv.get()
        coros = []
        if self.action:
            coros.append(self.action.start())
        if self.preaction:
            coros.append(self.preaction.start())
        if self.requester:
            coros.append(self.requester.start())
        if coros:
            await asyncio.wait(coros)

    def __call__(self) -> NetworkConnectionType:
        return self._context.run(self._new_connection)

    def _additional_connection_kwargs(self) -> Dict[str, Any]:
        return {}

    def _new_connection(self) -> NetworkConnectionType:
        context_cv.set(context_cv.get().copy())
        self.logger.debug('Creating new connection')
        return self.connection_cls(parent_name=self.full_name, peer_prefix=self.peer_prefix, action=self.action,
                                   preaction=self.preaction, requester=self.requester, dataformat=self.dataformat,
                                   pause_reading_on_buffer_size=self.pause_reading_on_buffer_size, logger=self.logger,
                                   allowed_senders=self.allowed_senders, aliases=self.aliases,
                                   codec_config=self.codec_config, **self._additional_connection_kwargs())

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def set_logger(self, logger: Logger) -> None:
        self.logger = logger

    def set_name(self, full_name: str, peer_prefix: str) -> None:
        self.full_name = full_name
        self.peer_prefix = peer_prefix

    def is_owner(self, connection: NetworkConnectionType) -> bool:
        return connection.is_child(self.full_name)

    async def wait_num_has_connected(self, num: int) -> None:
        await connections_manager.wait_num_has_connected(self.full_name, num)

    async def wait_num_connected(self, num: int) -> None:
        await connections_manager.wait_num_connections(self.full_name, num)

    async def wait_all_messages_processed(self) -> None:
        await connections_manager.wait_all_messages_processed(self.full_name)

    async def wait_all_closed(self) -> None:
        await connections_manager.wait_num_connections(self.full_name, 0)

    async def close_actions(self) -> None:
        coros = []
        if self.action:
            coros.append(self.action.close())
        if self.preaction:
            coros.append(self.preaction.close())
        if self.requester:
            coros.append(self.requester.close())
        if coros:
            await asyncio.wait(coros)

    def close_all_connections(self, exc: Optional[Exception]) -> None:
        connections = filter(self.is_owner, connections_manager)
        for conn in list(connections):
            conn.close()

    async def close(self) -> None:
        await self.wait_num_connected(0)
        await self.close_actions()
        connections_manager.clear_server(self.full_name)


@dataclass
class StreamServerProtocolFactory(BaseProtocolFactory):
    connection_cls = TCPServerConnection


@dataclass
class StreamClientProtocolFactory(BaseProtocolFactory):
    connection_cls = TCPClientConnection


@dataclass
class BaseDatagramProtocolFactory(asyncio.DatagramProtocol, BaseProtocolFactory):
    connection_cls: NetworkConnectionType = UDPServerConnection
    transport = None
    sock = None

    def __call__(self: ProtocolFactoryType) -> ProtocolFactoryType:
        return self

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')[0:2]

    def close_all_connections(self, exc: Optional[Exception]) -> None:
        connections = filter(self.is_owner, connections_manager)
        for conn in list(connections):
            conn.connection_lost(exc)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.logger.manage_error(exc)
        self.close_all_connections(exc)

    def error_received(self, exc: Optional[Exception]) -> None:
        self.logger.manage_error(exc)

    def new_peer(self, addr: Tuple[str, int] = None) -> NetworkConnectionType:
        conn = self._context.run(self._new_connection)
        transport = DatagramTransportWrapper(self.transport, addr)
        ok = conn.connection_made(transport)
        if ok:
            return conn

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple[str, int]) -> None:
        addr = addr[0:2]
        peer = self.connection_cls.get_peername(self.peer_prefix, addr_tuple_to_str(addr), addr_tuple_to_str(self.sock))
        conn = connections_manager.get(peer, None)
        if conn:
            conn.data_received(data)
        else:
            conn = self.new_peer(addr)
            if conn:
                conn.data_received(data)

    async def close(self) -> None:
        self.close_all_connections(None)
        await super().close()


@dataclass
class DatagramServerProtocolFactory(BaseDatagramProtocolFactory):
    connection_cls: NetworkConnectionType = UDPServerConnection


@dataclass
class DatagramClientProtocolFactory(BaseDatagramProtocolFactory):
    connection_cls: NetworkConnectionType = UDPClientConnection
