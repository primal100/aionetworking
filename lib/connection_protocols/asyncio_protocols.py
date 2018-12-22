import asyncio
from concurrent import futures
import logging
import time

from lib import settings
from lib.utils import plural, log_exception

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.messagemanagers.base import BaseMessageManager
else:
    BaseMessageManager = None

logger = logging.getLogger(settings.LOGGER_NAME)


executor = futures.ProcessPoolExecutor()


class BaseProtocolMixin:
    name: str = ''
    alias: str = ''
    peer: str = ''
    sock = (None, None)
    other_ip: str = None
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

    def send(self, msg):
        raise NotImplementedError

    def send_msg(self, msg):
        self.send(msg)
        if logger.isEnabledFor(logging.INFO):
            self.sent_msgs += 1
            self.sent_bytes += len(msg)

    def check_other(self, other_ip):
        return self.manager.check_sender(other_ip)

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        self.other_ip = peer[0]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.sock = ':'.join(str(prop) for prop in sock)
        self.alias = self.check_other(self.other_ip)
        logger.info('New %s connection from %s to %s', self.name, self.client, self.server)

    @staticmethod
    def manage_error(exc):
        if exc:
            logger.error(log_exception(exc))

    def connection_lost(self, exc):
        self.manage_error(exc)
        logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        logger.info('%s and %s kb were sent during session', plural(self.sent_msgs, 'message'), self.sent_bytes / 1024)
        logger.info('%s and %s kb were received during session', plural(self.received_msgs, 'message'), self.received_bytes / 1024)
        self.check_last_message_processed()

    def send_msgs(self, msgs):
        for msg in msgs:
            self.send_msg(msg)

    def check_last_message_processed(self):
        if self.received_msgs and self.received_msgs == self.processed_msgs:
            seconds = self.last_message_processed - self.first_message_received
            kb = self.received_bytes / 1024
            rate = kb / seconds
            logger.info('%s kb from %s were processed in %2.2f ms, %2.2f kb/s', kb, self.alias, seconds * 1000, rate)

    def task_callback(self, future):
        exc = future.exception()
        self.manage_error(exc)
        responses = future.result()
        if responses:
            self.send_msgs(responses)
        if logger.isEnabledFor(logging.INFO):
            self.processed_msgs += 1
            self.last_message_processed = time.time()
            if self.transport.is_closing():
                self.check_last_message_processed()

    def on_data_received(self, sender, data):
        if logger.isEnabledFor(logging.INFO):
            logger.debug("Received msg from %s", sender)
            if not self.first_message_received:
                self.first_message_received = time.time()
            self.received_msgs += 1
            self.received_bytes += len(data)
        f = executor.submit(self.manager.handle_message, self.alias, data)
        f.add_done_callback(self.task_callback)
        #self.processed_msgs += 1
        #self.last_message_processed = time.time()
        #self.check_last_message_processed()
        #task.add_done_callback(self.task_callback)


class TCP(BaseProtocolMixin, asyncio.Protocol):

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def data_received(self, data):
        self.on_data_received(self.other_ip, data)

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
