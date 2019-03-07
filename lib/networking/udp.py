import asyncio
import logging
import time
from functools import partial

from .asyncio_protocols import BaseProtocolMixin
from .mixins import ServerProtocolMixin, ClientProtocolMixin
from .logging import SimpleConnectionLogger

from lib.utils import addr_tuple_to_str


class UDP(BaseProtocolMixin, asyncio.DatagramProtocol):

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def send(self, msg):
        self.transport.sendto(msg)

    def error_received(self, exc):
        self.logger.manage_error(exc)


class UDPServerClientProtocol(ServerProtocolMixin, UDP):
    name = 'UDP Server'

    def send(self, msg):
        self.transport.sendto(msg, addr=(self.peer_ip, self.peer_port))

    def connection_lost(self, exc):
        self.logger.manage_error(exc)
        self.stats_logger.connection_finished()

    def close_connection(self):
        pass


class UDPClientProtocol(ClientProtocolMixin, UDP):
    name = 'UDP Client'


class UDPServerProtocol(asyncio.DatagramProtocol):
    transport = None
    logger_name = 'receiver'
    sock = (None, None)
    name = "UDP Listener"
    client_protocol_class = UDPServerClientProtocol

    @classmethod
    def with_config(cls, logger, cp=None, **kwargs):
        client_protocol_cls = cls.client_protocol_class.with_config(logger, cp=cp)
        cls._logger = logger or cls.logger_name
        return partial(cls, client_protocol_cls=client_protocol_cls, logger=logger, **kwargs)

    @property
    def server(self) -> str:
        return self.sock

    def __init__(self, manager, client_protocol_cls=None, logger=None):
        self.client_protocol_class = client_protocol_cls or self.client_protocol_class
        self.manager = manager
        self.clients = {}
        self.closed_event = asyncio.Event()
        logger = logger or logging.getLogger(self.logger_name)
        self.logger = SimpleConnectionLogger(logger, {})

    def connection_made(self, transport: transports.BaseTransport):
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')

    def connection_lost(self, exc: Optional[Exception]):
        self.logger.manage_error(exc)
        connections = list(self.clients.values())
        for conn in connections:
            conn.connection_lost(None)
        self.clients.clear()
        self.closed_event.set()

    async def wait_closed(self):
        await self.closed_event.wait()

    def error_received(self, exc: Exception):
        self.logger.manage_error(exc)

    def new_sender(self, addr, src):
        connection_protocol = self.client_protocol_class(self.manager)
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
