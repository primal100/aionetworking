import asyncio
import definitions
import logging

logger = logging.getLogger(definitions.LOGGER_NAME)


class BaseProtocolMixin:
    name = ''
    peer_str = ''
    peer = (None, None)
    sock = (None, None)
    client_str = None
    server_str = None
    other_ip = None
    transport = None

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        self.other_ip = peer[0]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.sock = ':'.join(str(prop) for prop in sock)
        logger.info('New', self.name, 'connection from', self.client, 'to', self.server)

    def manage_error(self, exc):
        if exc:
            error = '{} {}'.format(exc, self.peer)
            print(error)
            logger.error(error)

    def connection_lost(self, exc):
        self.manage_error(exc)
        logger.info(self.name, 'connection from', self.client_str, 'to', self.server_str, 'has been closed')


class ClientProtocolMixin(BaseProtocolMixin):

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


class TCPClientProtocol(ClientProtocolMixin, asyncio.Protocol):
    name = 'TCP Client'


class UDPClientProtocol(ClientProtocolMixin, asyncio.DatagramProtocol):
    name = 'UDP Client'

    def error_received(self, exc):
        self.manage_error(exc)


class ServerProtocolMixin(BaseProtocolMixin):

    def __init__(self, receiver):
        self.receiver = receiver

    @property
    def client(self) -> str:
        return self.peer

    @property
    def server(self) -> str:
        return self.sock

    def on_data_received(self, sender, data):
        asyncio.create_task(self.receiver.handle_message(sender, data))


class TCPServerProtocol(ServerProtocolMixin, asyncio.Protocol):
    name = 'TCP Server'

    def data_received(self, data):
        self.on_data_received(self.other_ip, data)


class UDPServerProtocol(ServerProtocolMixin, asyncio.DatagramProtocol):
    name = 'UDP Server'

    def error_received(self, exc):
        self.manage_error(exc)

    def datagram_received(self, data, sender):
        self.on_data_received(sender, data)
