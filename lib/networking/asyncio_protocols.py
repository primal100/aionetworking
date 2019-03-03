import asyncio
from asyncio import transports
import logging
import time

from lib import messagemanagers
from lib.utils import log_exception, addr_tuple_to_str

from typing import TYPE_CHECKING
from typing import Optional, Union, Text, Tuple

if TYPE_CHECKING:
    from asyncio import transports
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseProtocolMixin:
    name: str = ''
    logger_name: str = ''
    alias: str = ''
    peer: str = ''
    sock = (None, None)
    peer_ip: str = None
    peer_port: int = 0
    transport = None
    sent_msgs: int = 0
    sent_bytes: int = 0
    received_msgs: int = 0
    received_bytes: int = 0
    processed_msgs: int = 0
    first_message_received: float = 0
    last_message_processed: float = 0

    def __init__(self, manager: BaseMessageManager, logger_name=None):
        logger_name = logger_name or self.logger_name
        self.manager = manager
        self.logger = logging.getLogger(logger_name)
        self.stats_log = logging.getLogger("%s.stats" % logger_name)

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    @property
    def sent_kbs(self):
        return self.sent_bytes / 1024

    @property
    def received_kbs(self):
        return self.received_bytes / 1024

    @property
    def sent_mbs(self):
        return self.sent_kbs / 1024

    @property
    def received_mbs(self):
        return self.received_kbs / 1024

    @property
    def processing_time(self):
        return self.last_message_processed - self.first_message_received

    @property
    def rate(self):
        return self.received_kbs / self.processing_time

    def send(self, msg):
        raise NotImplementedError

    def send_msg(self, msg):
        self.send(msg)
        if self.stats_log.isEnabledFor(logging.INFO):
            self.sent_msgs += 1
            self.sent_bytes += len(msg)

    def check_other(self, peer_ip):
        return self.manager.check_sender(peer_ip)

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.define_sock_peer(sock, peer)
        if connection_ok:
            self.logger.info('New %s connection from %s to %s', self.name, self.client, self.server)

    def define_sock_peer(self, sock, peer):
        self.peer_ip = peer[0]
        self.peer_port = peer[1]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.sock = ':'.join(str(prop) for prop in sock)
        try:
            self.alias = self.check_other(self.peer_ip)
            return True
        except messagemanagers.MessageFromNotAuthorizedHost:
            self.close_connection()
            return False

    def close_connection(self):
        self.transport.close()

    def manage_error(self, exc):
        if exc:
            self.logger.error(log_exception(exc))

    def connection_lost(self, exc):
        self.manage_error(exc)
        self.logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        if self.stats_log.isEnabledFor(logging.INFO):
            self.check_last_message_processed()

    def send_msgs(self, msgs):
        for msg in msgs:
            self.send_msg(msg)

    @property
    def stats_extra(self):
        return {'peer_ip': self.peer_port, 'peer_port': self.peer_port, 'peer': self.peer, 'sock': self.sock,
                'alias': self.alias, 'first_message_received': self.first_message_received,
                'received_msgs': self.received_msgs,
                'received_bytes': self.received_bytes, 'processed_msgs': self.processed_msgs,
                'last_message_processed': self.last_message_processed}

    def check_last_message_processed(self):
        if self.received_msgs and self.received_msgs == self.processed_msgs:
            self.stats_log.info('', extra=self.stats_extra)
            #self.stats_log.info('%s kb from %s were processed in %2.2f ms, %2.2f kb/s', self.received_kbs, self.alias, seconds * 1000, rate)

    def task_callback(self, future):
        exc = future.exception()
        self.manage_error(exc)
        responses = future.result()
        if responses:
            self.send_msgs(responses)
        self.last_message_processed = time.time()
        if self.stats_log.isEnabledFor(logging.INFO):
            self.processed_msgs += 1
            if self.transport.is_closing():
                self.check_last_message_processed()

    def on_data_received(self, data, timestamp=None):
        self.logger.debug("Received msg from %s", self.alias)
        if self.stats_log.isEnabledFor(logging.INFO):
            if not self.first_message_received:
                self.first_message_received = time.time()
            self.received_msgs += 1
            self.received_bytes += len(data)
        task = self.manager.handle_message(self.alias, data, timestamp=timestamp)
        task.add_done_callback(self.task_callback)


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
        self.manage_error(exc)


class ClientProtocolMixin:
    logger_name = 'sender'

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


class ServerProtocolMixin:
    logger_name = 'receiver'

    @property
    def client(self) -> str:
        if self.alias:
            return '%s(%s)' % (self.alias, self.peer)
        return self.peer

    @property
    def server(self) -> str:
        return self.sock


class TCPServerProtocol(ServerProtocolMixin, TCP):
    name = 'TCP Server'


class TCPClientProtocol(ClientProtocolMixin, TCP):
    name = 'TCP Client'


class UDPServerClientProtocol(ServerProtocolMixin, UDP):
    name = 'UDP Server'

    def send(self, msg):
        self.transport.sendto(msg, addr=(self.peer_ip, self.peer_port))

    def connection_lost(self, exc):
        self.manage_error(exc)
        if self.stats_log.isEnabledFor(logging.INFO):
            self.check_last_message_processed()

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

    def manage_error(self, exc):
        if exc:
            self.log.error(log_exception(exc))

    @property
    def server(self) -> str:
        return self.sock

    def __init__(self, manager: BaseMessageManager, logger_name=None):
        self.logger_name = logger_name or self.logger_name
        self.manager = manager
        self.log = logging.getLogger(self.logger_name)
        self.clients = {}
        self.closed_event = asyncio.Event()

    def connection_made(self, transport: transports.BaseTransport):
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')

    def connection_lost(self, exc: Optional[Exception]):
        self.manage_error(exc)
        connections = list(self.clients.values())
        for conn in connections:
            conn.connection_lost(None)
        self.clients.clear()
        self.closed_event.set()

    async def wait_closed(self):
        await self.closed_event.wait()

    def error_received(self, exc: Exception):
        self.manage_error(exc)

    def new_sender(self, addr, src):
        connection_protocol = self.client_protocol_class(self.manager, logger_name=self.logger_name)
        connection_ok = connection_protocol.define_sock_peer(self.sock, addr)
        if connection_ok:
            self.clients[src] = connection_protocol
            self.log.info('%s on %s started receiving messages from %s', self.name, self.server, src)
            return connection_protocol
        return False

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple[str, int]):
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
