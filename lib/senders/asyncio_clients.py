import asyncio
import logging

from lib import settings
from lib.connection_protocols.asyncio_protocols import TCPClientProtocol, UDPClientProtocol
from .base import BaseNetworkClient

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseAsyncioClient(BaseNetworkClient):
    transport = None
    connection_protocol = None

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data):
        self.connection_protocol.send_msg(encoded_data)

    async def open_connection(self):
        raise NotImplementedError


class TCPClient(BaseAsyncioClient):
    sender_type = "TCP Client"
    transport = None
    connection_protocol = None

    async def open_connection(self):
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_connection(
            lambda: TCPClientProtocol(self.manager), self.host, self.port, ssl=self.ssl, local_addr=self.localaddr)


class UDPClient(BaseAsyncioClient):
    sender_type = "UDP Client"
    transport = None
    connection_protocol = None

    async def open_connection(self):
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            UDPClientProtocol, remote_addr=(self.host, self.port))
