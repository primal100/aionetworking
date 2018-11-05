import asyncio
import logging


import settings
from lib.utils import plural

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.receivers.base import BaseReceiver
else:
    BaseReceiver = None

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseProtocolMixin:
    name: str = ''
    alias: str = ''
    peer: str = ''
    sock = (None, None)
    other_ip: str = None
    transport = None
    num_msgs: int = 0
    num_bytes: int = 0
    direction: str = ''

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def check_other(self, other_ip):
        return other_ip

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        self.other_ip = peer[0]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.sock = ':'.join(str(prop) for prop in sock)
        self.alias = self.check_other(self.other_ip)
        logger.info('New %s connection from %s to %s', self.name, self.client, self.server)

    def manage_error(self, exc):
        if exc:
            error = '{} {}'.format(exc, self.peer)
            print(error)
            logger.error(error)

    def connection_lost(self, exc):
        self.manage_error(exc)
        logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        logger.info('%s and %s kb were %s during session', plural(self.num_msgs, 'message'), self.num_bytes / 1024,
                     self.direction)


class ClientProtocolMixin(BaseProtocolMixin):
    direction = 'sent'

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


class TCPClientProtocol(ClientProtocolMixin, asyncio.Protocol):
    name = 'TCP Client'


class UDPClientProtocol(ClientProtocolMixin, asyncio.DatagramProtocol):
    name = 'UDP Client'

    def error_received(self, exc):
        self.manage_error(exc)


class ServerProtocolMixin(BaseProtocolMixin):
    direction = 'received'

    def __init__(self, receiver: BaseReceiver):
        self.receiver = receiver

    @property
    def client(self) -> str:
        if self.alias:
            return '%s(%s)' % (self.alias, self.peer)
        return self.peer

    @property
    def server(self) -> str:
        return self.sock

    def on_data_received(self, sender, data):
        if logger.isEnabledFor(logging.INFO):
            self.num_msgs += 1
            self.num_bytes += len(data)
        self.receiver.handle_message(self.alias, data)

    def check_other(self, other_ip):
        return self.receiver.check_sender(other_ip)


class TCPServerProtocol(ServerProtocolMixin, asyncio.Protocol):
    name = 'TCP Server'

    def data_received(self, data):
        self.on_data_received(self.other_ip, data)


class UDPServerProtocol(ServerProtocolMixin, asyncio.DatagramProtocol):
    name = 'UDP Server'

    def error_received(self, exc):
        self.manage_error(exc)

    def datagram_received(self, data, sender):
        self.on_data_received(sender, data)
