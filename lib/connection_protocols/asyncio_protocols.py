import asyncio
import settings
import logging

from typing import TYPE_CHECKING, Sequence
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
    i = 0

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
        print(self.i)


class ClientProtocolMixin(BaseProtocolMixin):

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
        asyncio.create_task(self.receiver.handle_message(self.alias, data))

    def check_other(self, other_ip):
        return self.receiver.check_sender(other_ip)


class TCPServerProtocol(ServerProtocolMixin, asyncio.Protocol):
    name = 'TCP Server'

    def data_received(self, data):
        self.i += 1
        self.on_data_received(self.other_ip, data)


class UDPServerProtocol(ServerProtocolMixin, asyncio.DatagramProtocol):
    name = 'UDP Server'

    def error_received(self, exc):
        self.manage_error(exc)

    def datagram_received(self, data, sender):
        self.on_data_received(sender, data)
