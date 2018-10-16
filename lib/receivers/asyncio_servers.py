import asyncio
import logging
from .base import BaseServer

logger = logging.getLogger()


class ServerException(Exception):
    pass


class ServerProtocolMixin:
    transport = None
    peer_name = None
    src = None
    sender = None

    def __init__(self, receiver):
        self.receiver = receiver

    def connection_made(self, transport):
        self.transport = transport
        self.peer_name = self.transport.get_extra_info('peername')
        self.src = ':'.join(str(prop) for prop in self.peer_name)
        self.sender = self.peer_name[0]
        logger.info('New client connection from %s' % self.src)

    def connection_lost(self, exc):
        if exc:
            error = '{} {}'.format(exc, self.src)
            print(error)
            logger.error(error)
        else:
            logger.info('Client connection from %s closed' % self.src)

    def on_data_received(self, sender, data):
        asyncio.create_task(self.receiver.handle_message(sender, data))


class TCPServerProtocol(ServerProtocolMixin, asyncio.Protocol):

    def data_received(self, data):
        self.on_data_received(self.sender, data)


class UDPServerProtocol(ServerProtocolMixin, asyncio.DatagramProtocol):

    def datagram_received(self, data, sender):
        self.on_data_received(sender, data)


class TCPServerReceiver(BaseServer):
    receiver_type = "TCP Server"
    server = None

    def __init__(self, manager, config):
        super(TCPServerReceiver, self).__init__(manager, config)
        self.ssl_context = self.manage_ssl_params()

    async def start_server(self):
        self.server = await asyncio.get_event_loop().create_server(lambda: TCPServerProtocol(self), self.host,
                                                                   self.port,
                                                                   ssl=self.ssl_context)
        print('Serving %s on %s' % (self.receiver_type, self.server.sockets[0].getsockname()))
        async with self.server:
            await self.server.serve_forever()

    async def stop_server(self):
        self.server.stop_server()
        await self.server.wait_closed()


class UDPServerReceiver(TCPServerReceiver):
    receiver_type = "UDP Server"
    transport = None
    protocol = None

    async def start_server(self):
        self.transport, self.protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: UDPServerProtocol(self), local_addr=(self.host, self.port))
        print('Serving %s on %s' % (self.receiver_type, self.transport.sockets[0].getsockname()))

    async def stop_server(self):
        self.transport.close()