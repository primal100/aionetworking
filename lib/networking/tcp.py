import asyncio
from .asyncio_protocols import BaseNetworkProtocol
from .mixins import ClientProtocolMixin, ServerProtocolMixin


class TCP(BaseNetworkProtocol, asyncio.Protocol):

    def connection_lost(self, exc):
        super(TCP, self).connection_lost(exc)
        self.transport.close()

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def data_received(self, data):
        self.on_data_received(data)

    def send(self, msg):
        self.transport.write(msg)


class TCPServerProtocol(ServerProtocolMixin, TCP):
    name = 'TCP Server'
    parent_logger_name = 'receiver'


class TCPClientProtocol(ClientProtocolMixin, TCP):
    name = 'TCP Client'
    parent_logger_name = 'sender'
