import asyncio

from .base import BaseServer
from lib.connection_protocols.asyncio_protocols import TCPServerProtocol, UDPServerProtocol


class TCPServerReceiver(BaseServer):
    receiver_type = "TCP Server"
    ssl_allowed = True

    async def start_server(self):
        self.server = await asyncio.get_event_loop().create_server(lambda: TCPServerProtocol(self), self.host,
                                                                   self.port,
                                                                   ssl=self.ssl_context)
        socket = self.server.sockets[0]
        self.print_listening_message(socket)
        async with self.server:
            self.set_status_changed('started')
            await self.server.serve_forever()

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


class UDPServerReceiver(BaseServer):
    receiver_type = "UDP Server"
    transport = None
    protocol = None

    async def start_server(self):
        self.transport, self.protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: UDPServerProtocol(self), local_addr=(self.host, self.port))
        socket = self.transport.sockets[0]
        self.print_listening_message(socket)
        self.set_status_changed('started')

    async def stop_server(self):
        if self.transport:
            self.transport.close()
