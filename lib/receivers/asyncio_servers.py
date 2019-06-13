import asyncio
from abc import ABC, abstractmethod
from ssl import SSLContext

from pydantic.dataclasses import dataclass

from .base import BaseServer
from lib.conf.exceptions import ConfigurationException
from lib.networking.tcp import TCPServerProtocol, TCPOneWayServerProtocol
from lib.networking.udp import UDPServerProtocol, UDPServerOneWayProtocol
from lib.networking.ssl import ServerSideSSL


from typing import TYPE_CHECKING, NoReturn
if TYPE_CHECKING:
    from asyncio.base_events import Server
else:
    Server = None


@dataclass
class BaseTCPServerReceiver(ABC, BaseServer):
    server = None

    @abstractmethod
    async def get_server(self) -> Server: ...

    async def start_server(self) -> NoReturn:
        self.server = await self.get_server()
        async with self.server:
            self.print_listening_message(self.server.sockets)
            await self.server.serve_forever()

    async def stop_server(self) -> NoReturn:
        if self.server:
            self.server.close()


@dataclass
class BaseTCPServer(ABC, BaseTCPServerReceiver):

    ssl: ServerSideSSL = ServerSideSSL()
    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = 0

    def __post_init__(self):
        if self.ssl and not self.ssl_context:
            self.ssl_context = self.ssl.context

    async def get_server(self) -> Server:
        return await self.loop.create_server(self.protocol,
            self.host, self.port, ssl=self.ssl_context, ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class BaseUDPServer(ABC, BaseServer):
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


@dataclass
class TCPServerOneWay(BaseTCPServerReceiver):
    protocol: TCPOneWayServerProtocol = TCPOneWayServerProtocol()


@dataclass
class TCPServer(BaseTCPServerReceiver):
    receiver_type = "TCP Server"

    protocol: TCPServerProtocol = TCPServerProtocol()


@dataclass
class UDPServer(BaseUDPServer):
    protocol: UDPServerProtocol = UDPServerProtocol()


@dataclass
class UDPOneWayServer(BaseUDPServer):
    protocol: UDPServerOneWayProtocol = UDPServerOneWayProtocol()
