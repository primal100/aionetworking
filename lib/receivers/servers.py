from __future__ import annotations
import asyncio
from ssl import SSLContext

from dataclasses import dataclass

from .base import BaseServer, BaseTCPReceiver
from lib.networking.ssl import ServerSideSSL

from socket import socket
from typing import List


@dataclass
class TCPServer(BaseTCPReceiver):
    name = "TCP Server"

    ssl: ServerSideSSL = None
    ssl_handshake_timeout: int = 0

    def __post_init__(self):
        if isinstance(self.ssl, SSLContext):
            self.ssl = ServerSideSSL(context=self.ssl)

    async def get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_server(self.protocol_generator,
                                             host=self.host, port=self.port, ssl=self.ssl.context,
                                             ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class UDPServer(BaseServer):
    name = "UDP Server"
    transport: asyncio.DatagramTransport = None

    async def start_server(self) -> List[socket]:
        self.transport, self.protocol = await self.loop.create_datagram_endpoint(
            self.protocol_generator, local_addr=(self.host, self.port))
        return [self.transport.get_extra_info('socket')]
        #await self.protocol.check_senders_expired(self.expiry_minutes)

    async def stop_server(self) -> None:
        self.transport.close()

