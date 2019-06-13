from abc import ABC
import asyncio

from .mixins import BaseClientProtocol, BaseOneWayServerProtocol, BaseTwoWayServerProtocol


from typing import TYPE_CHECKING, AnyStr, ClassVar
if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass


@dataclass
class OneWayTCPMixin(asyncio.Protocol, ABC):

    def close_connection(self):
        self.transport.close()

    def data_received(self, data: AnyStr):
        self.on_data_received(data)


@dataclass
class TCPMixin(OneWayTCPMixin, ABC):

    def send(self, msg: AnyStr):
        self.transport.write(msg)


@dataclass
class TCPOneWayServerProtocol(BaseOneWayServerProtocol, OneWayTCPMixin):
    name = 'TCP Server'
    _connections: ClassVar = {}


@dataclass
class TCPServerProtocol(BaseTwoWayServerProtocol, TCPMixin):
    name = 'TCP Server'
    _connections: ClassVar = {}


@dataclass
class TCPClientProtocol(BaseClientProtocol, TCPMixin):
    name = 'TCP Client'
    _connections: ClassVar = {}
