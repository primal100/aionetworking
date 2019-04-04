import asyncio
from abc import ABC
from pydantic.dataclasses import dataclass

from .asyncio_protocols import BaseNetworkProtocol
from .mixins import ClientProtocolMixin, ServerProtocolMixin, OneWayServerProtocolMixin


from typing import ClassVar


@dataclass
class OneWayTCP(ABC, BaseNetworkProtocol, asyncio.Protocol):

    def close_connection(self):
        self.transport.close()

    def data_received(self, data):
        self.on_data_received(data)


@dataclass
class TCP(ABC, OneWayTCP):

    def send(self, msg):
        self.transport.write(msg)


@dataclass
class TCPOneWayServerProtocol(OneWayServerProtocolMixin, OneWayTCP):
    name = 'TCP Server'
    _connections: ClassVar = {}


@dataclass
class TCPServerProtocol(ServerProtocolMixin, TCP):
    name = 'TCP Server'
    _connections: ClassVar = {}


@dataclass
class TCPClientProtocol(ClientProtocolMixin, TCP):
    name = 'TCP Client'
    _connections: ClassVar = {}
