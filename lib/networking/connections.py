from __future__ import annotations
import asyncio
import contextvars
from datetime import datetime
from dataclasses import dataclass, field, replace

from .exceptions import MessageFromNotAuthorizedHost
from lib.actions.protocols import OneWaySequentialAction
from lib.formats.base import BufferObject
from lib.types import Type
from lib.utils_logging import p
from lib.wrappers.schedulers import TaskScheduler

from lib.formats.base import BaseCodec, BaseMessageObject
from lib.conf.logging import Logger, ConnectionLogger

from .protocols import DataProtocol, NetworkProtocol, ProtocolType, AdaptorProtocol, AdaptorProtocolGetattr

from typing import  AnyStr, ClassVar, MutableMapping, List, NoReturn, Tuple, TypeVar, Union
from typing_extensions import Protocol


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')



@dataclass
class BaseConnectionProtocol(DataProtocol, AdaptorProtocolGetattr, Protocol):
    name = ''
    connection_logger_cls = ConnectionLogger
    start_immediately = True

    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger = field(default=None, init=False, hash=False, compare=False, repr=False)
    context: MutableMapping = field(default_factory=dict)
    adaptor: AdaptorProtocol = field(default=None)
    dataformat: Type[BaseMessageObject] = None
    codec: BaseCodec = None
    preaction: OneWaySequentialAction = None
    parent_logger: Logger = Logger('receiver')
    parent: int = None
    timeout: Union[int, float] = 5

    def __post_init__(self) -> None:
        self.context['protocol_name'] = self.name
        if self.dataformat and not self.codec:
            self.codec: BaseCodec = self.dataformat.get_codec(logger=self.parent_logger, context=self.context)
        if self.start_immediately:
            self._initialize()

    def __getattr__(self, item):
        if self.adaptor:
            return getattr(self.adaptor, item)

    def _initialize(self) -> None:
        self.configure_context()
        self.adaptor = self._configure_adaptor()

    def __call__(self, **kwargs):
        return self._clone(**kwargs)

    def _clone(self: ProtocolType, **kwargs) -> ProtocolType:
        return replace(self, parent=id(self), **kwargs)

    def _configure_context(self) -> None:
        self.set_logger()
        self.codec.set_context(self.context, logger=self.logger)

    def is_owner(self, connection: ProtocolType) -> bool:
        return connection.parent == id(self)

    async def close(self) -> None:
        await self.adaptor.close()
        await self._scheduler.close(timeout=self.timeout)

    def set_logger(self) -> None:
        self.logger = self.parent_logger.get_connection_logger(is_receiver=self.is_receiver, context=self.context)

    def _manage_buffer(self, buffer: AnyStr, timestamp: datetime = None) -> None:
        self.logger.on_buffer_received(buffer)
        if self.preaction:
            buffer = BufferObject(buffer, received_timestamp=timestamp, logger=self.logger, context=self.context)
            self.preaction.do_many([buffer])

    def on_data_received(self, buffer: AnyStr, timestamp: datetime = None) -> None:
        timestamp = timestamp or datetime.now()
        self._manage_buffer(buffer, timestamp)
        msgs = self.codec.decode_buffer(buffer, received_timestamp=timestamp)
        self.process_msgs(msgs, buffer)


TransportType = TypeVar('TransportType', bound=asyncio.BaseTransport)


@dataclass
class NetworkConnectionProtocol(BaseConnectionProtocol, NetworkProtocol, Protocol):
    start_immediately = False
    sock = ('', 0)
    peer = ('', 0)
    peer_str = ''
    alias = ''
    transport: TransportType = None

    connections: ClassVar[MutableMapping[str, ProtocolType]] = {}
    aliases: dict = field(default_factory=dict)
    #allowed_senders: List[IPvAnyNetwork] = field(default_factory=tuple)

    def _raise_message_from_not_authorized_host(self, sender) -> NoReturn:
        msg = f"Received message from unauthorized host {sender}"
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
            self.parent_logger.debug('Alias found for %s: %s', host, alias)
        return alias

    def _check_peer(self, other_ip):
        if self._sender_valid(other_ip):
            return self._get_alias(other_ip)
        self._raise_message_from_not_authorized_host(other_ip)

    def finish_connection(self, exc: BaseException) -> None:
        self.logger.connection_finished(exc)
        self.connections.pop(self.peer_str, None)
        self.close_connection()

    def _update_context_with_connection_details(self):
        self.context['peer'] = self.peer
        self.context['sock'] = self.sock
        self.context['alias'] = self.alias

    def initialize(self, sock:  Tuple[str, int], peer: Tuple[str, int]) -> bool:
        self.peer = peer
        self.sock = sock
        try:
            self.alias = self._check_peer(self.peer)
            self._update_context_with_connection_details()
            self._configure_context()
            return True
        except MessageFromNotAuthorizedHost as exc:
            self.finish_connection(exc)
            return False

    def initialize_connection(self) -> None:
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.new_connection()
            self.peer_str = self.logger.tuple_to_str(peer)
            self.connections[self.peer_str] = self
            self.logger.debug('Connection opened. There %s now %s.', p.plural_verb('is', p.num(len(self.connections))),
                              p.no('active connection'))


@dataclass
class TCPConnection(asyncio.Protocol, NetworkConnectionProtocol):
    transport: asyncio.Transport = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.initialize_connection()

    def connection_lost(self, exc: BaseException) -> None:
        self.finish_connection(exc)

    def data_received(self, data: AnyStr) -> None:
        self.on_data_received(data)

    def close_connection(self) -> None:
        self.transport.close()

    def send(self, msg: AnyStr) -> None:
        self.transport.write(msg)

    def send_many(self, data_list: List[AnyStr]) -> None:
        self.transport.writelines(data_list)