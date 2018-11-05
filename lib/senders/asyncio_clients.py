import asyncio
import logging

import settings
from lib.connection_protocols.asyncio_protocols import TCPClientProtocol, UDPClientProtocol
from .base import BaseNetworkClient

logger = logging.getLogger(settings.LOGGER_NAME)


class TCPClient(BaseNetworkClient):
    sender_type = "TCP Client"
    transport = None
    connection_protocol = None

    async def open_connection(self):
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_connection(
            TCPClientProtocol, self.host, self.port, ssl=self.ssl, local_addr=self.localaddr)

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data):
        self.transport.write(encoded_data)
        if logger.isEnabledFor(logging.INFO):
            self.connection_protocol.num_msgs += 1
            self.connection_protocol.num_bytes += len(encoded_data)


class UDPClient(BaseNetworkClient):
    sender_type = "UDP Client"
    transport = None
    connection_protocol = None

    async def open_connection(self):
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            UDPClientProtocol, remote_addr=(self.host, self.port))

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data):
        self.transport.sendto(encoded_data)
