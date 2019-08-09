import asyncio
from pathlib import Path
from ssl import SSLContext

from dataclasses import dataclass, field

from lib.networking.types import ConnectionType
from lib.networking.ssl import ClientSideSSL
from .base import BaseClient, BaseNetworkClient


@dataclass
class TCPClient(BaseNetworkClient):
    name = "TCP Client"
    transport: asyncio.Transport = field(init=False, compare=False, default=None)

    #ssl: ClientSideSSL = None
    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = None

    """def __post_init__(self):
        if self.ssl and not self.ssl_context:
            self.ssl_context = self.ssl.context"""

    async def open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_connection(
            self.protocol_generator, self.host, self.port, ssl=self.ssl_context,
            local_addr=self.local_addr, ssl_handshake_timeout=self.ssl_handshake_timeout)
        return self.conn


@dataclass
class UnixClient(BaseClient):
    name = "Unix Client"
    path: Path = Path('/tmp/unix_server.socket')
    transport: asyncio.Transport = field(init=False, compare=False, default=None)

    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = None

    @property
    def dst(self) -> str:
        return str(self.path)

    async def open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_unix_connection(
            self.protocol_generator, path=str(self.path), ssl=self.ssl_context,
            ssl_handshake_timeout=self.ssl_handshake_timeout)
        return self.conn


@dataclass
class UDPClient(BaseNetworkClient):
    name = "UDP Client"
    transport: asyncio.DatagramTransport = field(init=False, compare=False, default=None)

    async def open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_datagram_endpoint(
            self.protocol_generator, remote_addr=(self.host, self.port), local_addr=self.local_addr)
        return self.conn
