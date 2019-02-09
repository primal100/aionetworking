import asyncio
import logging
import time

from lib import settings
from lib import messagemanagers
from lib.utils import log_exception

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.messagemanagers.base import BaseMessageManager
else:
    BaseMessageManager = None


logger = settings.get_logger('main')
stats = settings.get_logger('stats')


class BaseProtocolMixin:
    name: str = ''
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

    def __init__(self, manager: BaseMessageManager):
        self.manager = manager

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
        if stats.isEnabledFor(logging.INFO):
            self.sent_msgs += 1
            self.sent_bytes += len(msg)

    def check_other(self, peer_ip):
        return self.manager.check_sender(peer_ip)

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        self.peer_ip = peer[0]
        self.peer_port = peer[1]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.sock = ':'.join(str(prop) for prop in sock)
        try:
            self.alias = self.check_other(self.peer_ip)
            logger.info('New %s connection from %s to %s', self.name, self.client, self.server)
        except messagemanagers.MessageFromNotAuthorizedHost:
            self.transport.close()

    @staticmethod
    def manage_error(exc):
        if exc:
            logger.error(log_exception(exc))

    def connection_lost(self, exc):
        self.manage_error(exc)
        logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        if stats.isEnabledFor(logging.INFO):
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
            stats.info('', extra=self.stats_extra)
            #stats.info('%s kb from %s were processed in %2.2f ms, %2.2f kb/s', self.received_kbs, self.alias, seconds * 1000, rate)

    def task_callback(self, future):
        exc = future.exception()
        self.manage_error(exc)
        responses = future.result()
        if responses:
            self.send_msgs(responses)
        if stats.isEnabledFor(logging.INFO):
            self.processed_msgs += 1
            self.last_message_processed = time.time()
            if self.transport.is_closing():
                self.check_last_message_processed()

    def on_data_received(self, sender, data):
        logger.debug("Received msg from %s", sender)
        if stats.isEnabledFor(logging.INFO):
            if not self.first_message_received:
                self.first_message_received = time.time()
            self.received_msgs += 1
            self.received_bytes += len(data)
        task = asyncio.create_task(self.manager.handle_message(self.alias, data))
        task.add_done_callback(self.task_callback)


class TCP(BaseProtocolMixin, asyncio.Protocol):

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def data_received(self, data):
        self.on_data_received(self.peer_ip, data)

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

    def datagram_received(self, data, sender):
        self.on_data_received(sender, data)

    def error_received(self, exc):
        self.manage_error(exc)


class ClientProtocolMixin:

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


class ServerProtocolMixin:

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


class UDPServerProtocol(ServerProtocolMixin, UDP):
    name = 'UDP Server'


class UDPClientProtocol(ClientProtocolMixin, UDP):
    name = 'UDP Client'
