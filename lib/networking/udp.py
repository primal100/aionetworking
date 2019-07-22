from abc import ABC
import asyncio
from dataclasses import dataclass, replace
import time

from .mixins import BaseServerProtocol, BaseClientProtocol, BaseTwoWayServerProtocol
from lib.utils import addr_tuple_to_str

from typing import AnyStr, Sequence


@dataclass
class UDPMixin(asyncio.DatagramProtocol, ABC):
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

    def send(self, data: AnyStr):
        self.transport.sendto(data, addr=(self.peer_ip, self.peer_port))


@dataclass
class UDPServerOneWayProtocol(UDPMixin, BaseServerProtocol):
    name = 'UDP Server'

    def send(self, msg: AnyStr):
        raise NotImplementedError


@dataclass
class UDPServerProtocol(UDPMixin, BaseTwoWayServerProtocol):
    name = 'UDP Server'


@dataclass
class UDPClientProtocol(UDPMixin, BaseClientProtocol):
    name = 'UDP Client'
