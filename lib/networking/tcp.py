import asyncio
from .asyncio_protocols import BaseNetworkProtocol
from abc import ABC, abstractmethod
from .mixins import ClientProtocolMixin, ServerProtocolMixin


class TCP(ABC, BaseNetworkProtocol, asyncio.Protocol):

    def close_connection(self):
        self.transport.close()

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
