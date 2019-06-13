from abc import ABC
import asyncio
from dataclasses import replace
import time

from pydantic.dataclasses import dataclass

from .mixins import BaseOneWayServerProtocol, BaseClientProtocol, BaseTwoWayServerProtocol
from lib.utils import addr_tuple_to_str

from typing import AnyStr, ClassVar


@dataclass
class OneWayUDPMixin(asyncio.DatagramProtocol, ABC):
    expiry_minutes: int = 30

    def __call__(self):
        return self

    def error_received(self, exc):
        self.logger.manage_error(exc)

    def finish_connection(self, exc:Exception):
        super().connection_lost(exc)

    def connection_lost(self, exc: Exception):
        super().connection_lost(exc)
        for conn in self.clients.values():
            conn.finish_connection(exc)

    def new_sender(self, addr: str, src: str):
        connection_protocol = replace(self)
        connection_ok = connection_protocol.initialize(self.sock, addr)
        if connection_ok:
            self.clients[src] = connection_protocol
            self.logger.info('%s on %s started receiving messages from %s', self.name, self.server, src)
            return connection_protocol
        return None

    def datagram_received(self, data: AnyStr, addr: str):
        src = addr_tuple_to_str(addr)
        connection_protocol = self.clients.get(src, None)
        if connection_protocol:
            connection_protocol.on_data_received(data)
        else:
            connection_protocol = self.new_sender(addr, src)
            if connection_protocol:
                connection_protocol.on_data_received(data)

    async def check_senders_expired(self, expiry_minutes):
        now = time.time()
        connections = list(self.clients.values())
        for conn in connections:
            if (now - conn.last_message_processed) / 60 > expiry_minutes:
                conn.connection_lost(None)
                del self.clients[conn.peer]
        await asyncio.sleep(60)


@dataclass
class UDPMixin(OneWayUDPMixin, ABC):

    def send(self, msg: AnyStr):
        self.transport.sendto(msg, addr=(self.peer_ip, self.peer_port))


@dataclass
class UDPServerOneWayProtocol(BaseOneWayServerProtocol, OneWayUDPMixin):
    name = 'UDP Server'
    _connections: ClassVar = {}


@dataclass
class UDPServerProtocol(BaseTwoWayServerProtocol, UDPMixin):
    name = 'UDP Server'
    _connections: ClassVar = {}


@dataclass
class UDPClientProtocol(BaseClientProtocol, UDPMixin):
    name = 'UDP Client'
    _connections: ClassVar = {}
