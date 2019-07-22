from abc import ABC, abstractmethod
import asyncio

from .mixins import BaseClientProtocol, BaseServerProtocol, BaseTwoWayServerProtocol


from typing import AnyStr, Sequence


class TCPMixin(asyncio.Protocol, ABC):

    def close_connection(self) -> None:
        self.transport.close()

    def data_received(self, data: AnyStr) -> None:
        self.on_data_received(data)

    def send(self, msg: AnyStr) -> None:
        self.transport.write(msg)

    def send_many(self, data_list: Sequence[AnyStr]) -> None:
        self.transport.writelines(data_list)


class TCPOneWayServerProtocol(BaseServerProtocol, TCPMixin):
    name = 'TCP Server'

    def send(self, data: AnyStr) -> None:
        pass


class TCPServerProtocol(BaseTwoWayServerProtocol, TCPMixin):
    name = 'TCP Server'


class TCPClientProtocol(BaseClientProtocol, TCPMixin):
    name = 'TCP Client'
