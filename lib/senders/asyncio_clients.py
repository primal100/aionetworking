from ssl import SSLContext

from pydantic.dataclasses import dataclass

from lib.conf.exceptions import ConfigurationException
from lib.networking.tcp import TCPClientProtocol
from lib.networking.udp import UDPClientProtocol
from lib.networking.ssl import ClientSideSSL
from .base import BaseNetworkClient


@dataclass
class TCPClient(BaseNetworkClient):
    sender_type = "TCP Client"

    protocol: TCPClientProtocol = TCPClientProtocol()
    ssl: ClientSideSSL = ClientSideSSL()
    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = 0

    def __post_init__(self):
        if self.ssl and not self.ssl_context:
            self.ssl_context = self.ssl.context

    async def open_connection(self) -> TCPClientProtocol:
        self.transport, self.conn = await self.loop.create_connection(
            self.protocol, self.host, self.port, ssl=self.ssl_context,
            local_addr=self.localaddr, ssl_handshake_timeout=self.ssl_handshake_timeout)
        return self.conn

    async def close_connection(self):
        self.transport.close()


@dataclass
class UDPClient(BaseNetworkClient):
    sender_type = "UDP Client"
    protocol: UDPClientProtocol = UDPClientProtocol()

    async def open_connection(self):
        if self.loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.conn = await self.loop.create_datagram_endpoint(
            self.protocol, remote_addr=(self.host, self.port), local_addr=self.localaddr)
        return self.conn
