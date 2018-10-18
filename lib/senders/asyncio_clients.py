import asyncio
import logging
from .base import BaseNetworkClient

logger = logging.getLogger('messageManager')


class ClientProtocolMixin:
    name = ''
    transport = None

    def __init__(self, client):
        self.client = client

    def connection_made(self, transport):
        self.transport = transport
        logger.info('%s connected to %s' % (self.name, self.client.dst))

    def connection_lost(self, exc):
        if exc:
            error = '{} {}'.format(exc, self.client.dst)
            print(error)
            logger.error(error)
        else:
            logger.info('%s connection to %s has been closed' % (self.name, self.client.dst))


class TCPClientProtocol(ClientProtocolMixin, asyncio.Protocol):
    name = 'TCP Client'


class UDPClientProtocol(ClientProtocolMixin, asyncio.DatagramProtocol):
    name = 'UDP Client'

    def error_received(self, exc):
        if exc:
            error = '{} {}'.format(exc, self.client.dst)
            print(error)
            logger.error(error)


class TCPClient(BaseNetworkClient):
    sender_type = "TCP Client"
    transport = None
    protocol = None

    async def open_connection(self):
        self.transport, self.protocol = await asyncio.get_event_loop().create_connection(
            lambda: TCPClientProtocol(self), self.host, self.port, ssl=self.ssl, local_addr=self.localaddr)

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data):
        self.transport.write(encoded_data)


class UDPClient(BaseNetworkClient):
    sender_type = "UDP Client"
    transport = None
    protocol = None

    async def open_connection(self):
        self.transport, self.protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: UDPClientProtocol(self), remote_addr=(self.host, self.port))

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data):
        self.transport.sendto(encoded_data)
