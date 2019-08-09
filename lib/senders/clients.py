import asyncio
from ssl import SSLContext

from dataclasses import dataclass, field

from lib.networking.types import ConnectionType
from lib.networking.ssl import ClientSideSSL
from .base import BaseNetworkClient


@dataclass
class TCPClient(BaseNetworkClient):
    name = "TCP Client"
    transport: asyncio.Transport = field(init=False, compare=False)

    ssl: ClientSideSSL = None
    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = 0

    def __post_init__(self):
        if self.ssl and not self.ssl_context:
            self.ssl_context = self.ssl.context

    async def open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_connection(
            self.protocol_generator, self.host, self.port, ssl=self.ssl_context,
            local_addr=self.local_addr, ssl_handshake_timeout=self.ssl_handshake_timeout)
        return self.conn


@dataclass
class UDPClient(BaseNetworkClient):
    name = "UDP Client"
    transport: asyncio.DatagramTransport = field(init=False, compare=False)

    async def open_connection(self):
        self.transport, self.conn = await self.loop.create_datagram_endpoint(
            self.protocol_generator, remote_addr=(self.host, self.port), local_addr=self.local_addr)
        return self.conn
