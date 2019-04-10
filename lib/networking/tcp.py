import asyncio
from abc import ABC
from pydantic.dataclasses import dataclass

from .mixins import BaseClientProtocol, BaseOneWayServerProtocol, BaseTwoWayServerProtocol


from typing import TYPE_CHECKING, AnyStr, ClassVar
if TYPE_CHECKING:
    from .mixins import NetworkProtocolMixin
else:
    NetworkProtocolMixin = object


@dataclass
class OneWayTCPMixin(ABC, NetworkProtocolMixin, asyncio.Protocol):

    def close_connection(self):
        self.transport.close()

    def data_received(self, data: AnyStr):
        self.on_data_received(data)


@dataclass
class TCPMixin(ABC, OneWayTCPMixin):

    def send(self, msg: AnyStr):
        self.transport.write(msg)


@dataclass
class TCPOneWayServerProtocol(OneWayTCPMixin, BaseOneWayServerProtocol):
    name = 'TCP Server'
    _connections: ClassVar = {}


@dataclass
class TCPServerProtocol(TCPMixin, BaseTwoWayServerProtocol):
    name = 'TCP Server'
    _connections: ClassVar = {}


@dataclass
class TCPClientProtocol(TCPMixin, BaseClientProtocol):
    name = 'TCP Client'
    _connections: ClassVar = {}
