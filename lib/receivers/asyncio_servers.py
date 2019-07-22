import asyncio
from abc import ABC, abstractmethod
from ssl import SSLContext

from pydantic.dataclasses import dataclass

from .base import BaseServer
from lib.conf.exceptions import ConfigurationException
from lib.networking.tcp import TCPServerProtocol, TCPOneWayServerProtocol
from lib.networking.udp import UDPServerProtocol, UDPServerOneWayProtocol
from lib.networking.ssl import ServerSideSSL


from typing import TYPE_CHECKING, NoReturn, Union
if TYPE_CHECKING:
    from asyncio.base_events import Server
else:
    Server = None


@dataclass
class BaseTCPServerReceiver(BaseServer, ABC):
    server = None

    @abstractmethod
    async def get_server(self) -> Server: ...

    async def start_server(self) -> NoReturn:
        self.server = await self.get_server()
        self.print_listening_message(self.server.sockets)

    async def stop_server(self) -> NoReturn:
        if self.server:
            self.server.close()


@dataclass
class BaseTCPServer(BaseTCPServerReceiver, ABC):
    receiver_type = "TCP Server"

    ssl: ServerSideSSL = ServerSideSSL()
    ssl_handshake_timeout: int = 0

    def __post_init__(self):
        if isinstance(self.ssl, SSLContext):
            self.ssl = ServerSideSSL(_context=self.ssl)

    async def get_server(self) -> Server:
        return await self.loop.create_server(self.protocol,
            self.host, self.port, ssl=self.ssl.context, ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class BaseUDPServer(BaseServer, ABC):
    receiver_type = "UDP Server"
    transport = None

    async def start_server(self) -> NoReturn:
        if self.loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.protocol = await self.loop.create_datagram_endpoint(
            self.protocol, local_addr=(self.host, self.port))
        self.print_listening_message([self.transport.get_extra_info('socket')])
        await self.protocol.check_senders_expired(self.expiry_minutes)

    async def stop_server(self) -> NoReturn:
        if self.transport:
            self.transport.close()

    async def started(self) -> NoReturn:
        while not self.transport:
            await asyncio.sleep(0.001)

    async def stopped(self) -> NoReturn:
        if self.transport and self.transport.is_closing():
            await self.protocol.wait_closed()


@dataclass(config={'arbitrary_types_allowed': True})
class TCPServer(BaseTCPServerReceiver):
    protocol: Union[TCPOneWayServerProtocol, TCPServerProtocol] = None


@dataclass(config={'arbitrary_types_allowed': True})
class UDPServer(BaseUDPServer):
    protocol: Union[UDPServerOneWayProtocol, UDPServerProtocol] = None
