from abc import ABC, abstractmethod
from asyncio import protocols, transports
from dataclasses import dataclass, field, replace
import time

from lib.utils import addr_tuple_to_str
from lib.utils_logging import p
from lib.wrappers.periodic import call_cb_periodic

from typing import Any, ClassVar, Dict, Optional, Union, Text, Tuple


@dataclass
class BaseProtocol(ABC):
    logger = None
    transport = None
    sock = None
    connections: ClassVar = {}

    def __call__(self):
        return replace(self)


@dataclass
class BaseNetworkProtocol(BaseProtocol, ABC):
    _adaptor: Any
    peer = None
    sock = None

    def initialize(self, sock, peer) -> bool:
        connection_ok = self._adaptor.initialize(sock, peer)
        if connection_ok:
            self.logger.new_connection()
            self._connections[self.peer] = self
            self.logger.debug('Connection opened. There %s now %s.',
                              p.plural_verb('is', p.num(len(self._connections))),
                              p.no('active connection'))
        return connection_ok

    def on_connection_made(self, transport) -> None:
        self.transport = transport
        self.peer = self.transport.get_extra_info('peername')
        self.sock = self.transport.get_extra_info('sockname')
        self.initialize(self.sock, self.peer)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._adaptor.close(exc)
        self.transport.close()

    def on_data_received(self, data: bytes) -> None:
        for response in self._adaptor.data_received(data):
            self.send(response)

    @abstractmethod
    def send(self, data: bytes):
        raise NotImplementedError


class TCP(BaseNetworkProtocol, protocols.Protocol):
    _connections: ClassVar = {}

    def connection_made(self, transport: transports.Transport) -> None:
        self.on_connection_made(transport)

    def data_received(self, data: bytes) -> None:
        self.on_data_received(data)

    def send(self, data: bytes):
        self.transport.write(data)


@dataclass
class UDP(BaseNetworkProtocol, protocols.DatagramProtocol):
    def connection_made(self, transport: transports.DatagramTransport) -> None:
        self.transport = transport
        self._adaptor.connection_made(transport)

    def error_received(self, exc: Exception) -> None:
        self._adaptor.manage_error(exc)

    def send(self, data: bytes):
        self.transport.sendto(data, addr=self.peer)


@dataclass
class UDPServer(BaseProtocol, protocols.DatagramProtocol):
    expiry_minutes: int = 30
    _clients: Dict = field(default_factory=dict, init=False, repr=False, hash=False, compare=False)
    name = 'UDP Server'
    transport = None
    protocol: UDP = UDP(None)
    _stop_event = None

    def connection_made(self, transport: transports.DatagramTransport) -> None:
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')
        self._stop_event = call_cb_periodic(60, self.check_senders_expired())

    def connection_lost(self, exc: Exception):
        self._stop_event.set()
        self.transport.close()
        for conn in self._clients.values():
            conn.connection_lost(exc)

    def error_received(self, exc: Exception) -> None:
        pass

    def new_sender(self, addr: tuple, src: str):
        connection_protocol = self.protocol()
        connection_ok = connection_protocol.initialize(self.sock, addr)
        if connection_ok:
            self._clients[src] = connection_protocol
            self.logger.info('%s on %s started receiving messages from %s', self.name, self.sock, src)
            return connection_protocol
        return None

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple[str, int]) -> None:
        src = addr_tuple_to_str(addr)
        connection_protocol = self._clients.get(src)
        if not connection_protocol:
            connection_protocol = self.new_sender(addr, src)
        connection_protocol.data_received(data)

    def check_senders_expired(self):
        now = time.time()
        for key, conn in self._clients.items():
            if (now - conn.last_message_processed) / 60 > self.expiry_minutes:
                conn.connection_lost(None)
                del self._clients[key]
