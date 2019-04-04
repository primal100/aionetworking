from abc import ABC
import asyncio
from dataclasses import replace
import time

from pydantic.dataclasses import dataclass

from .asyncio_protocols import BaseNetworkProtocol
from .mixins import OneWayServerProtocolMixin, BaseServerProtocolMixin, ServerProtocolMixin, ClientProtocolMixin
from lib.utils import addr_tuple_to_str

from typing import ClassVar


@dataclass
class UDPServerMixin(ABC, BaseServerProtocolMixin):
    expiry_minutes: int = 30

    def connection_lost(self, exc):
        super().connection_lost(exc)
        for conn in self.clients.values():
            conn.connection_lost(None)

    def new_sender(self, addr, src):
        connection_protocol = replace(self)
        connection_ok = connection_protocol.initialize(self.sock, addr)
        if connection_ok:
            self.clients[src] = connection_protocol
            self.logger.info('%s on %s started receiving messages from %s', self.name, self.server, src)
            return connection_protocol
        return None

    def datagram_received(self, data, addr):
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
class OneWayUDP(ABC, BaseNetworkProtocol, asyncio.DatagramProtocol):

    def __call__(self):
        return self

    def error_received(self, exc):
        self.logger.manage_error(exc)


@dataclass
class UDP(ABC, OneWayUDP):

    def send(self, msg):
        self.transport.sendto(msg, addr=(self.peer_ip, self.peer_port))


@dataclass
class UDPServerOneWayProtocol(OneWayServerProtocolMixin, UDPServerMixin, UDP):
    name = 'UDP Server'
    _connections: ClassVar = {}


@dataclass
class UDPServerProtocol(ServerProtocolMixin, UDP):
    name = 'UDP Server'
    _connections: ClassVar = {}


@dataclass
class UDPClientProtocol(ClientProtocolMixin, UDP):
    name = 'UDP Client'
    _connections: ClassVar = {}
