import asyncio
from .asyncio_protocols import BaseProtocolMixin
from .mixins import ClientProtocolMixin, ServerProtocolMixin


class TCP(BaseProtocolMixin, asyncio.Protocol):

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


class TCPClientProtocol(ClientProtocolMixin, TCP):
    name = 'TCP Client'
