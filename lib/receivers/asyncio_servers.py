import asyncio

from .base import BaseServer
from lib.connection_protocols.asyncio_protocols import TCPServerProtocol, UDPServerProtocol


class TCPServerReceiver(BaseServer):
    receiver_type = "TCP Server"
    ssl_allowed = True

    async def start_server(self):
        self.server = await asyncio.get_event_loop().create_server(
            lambda: TCPServerProtocol(self.manager),
            self.host, self.port, ssl=self.ssl_context)

        async with self.server:
            self.print_listening_message(self.server.sockets)
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

    async def start_server(self, started_event):
        self.transport, self.protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: UDPServerProtocol(self.manager), local_addr=(self.host, self.port))
        self.print_listening_message(self.transport.sockets)
        self.set_status_changed(started_event, 'started')

    async def stop_server(self):
        if self.transport:
            self.transport.close()
