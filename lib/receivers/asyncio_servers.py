import asyncio
from functools import partial
from collections import ChainMap

from .base import BaseServer
from lib.conf.logging import Logger
from lib.networking.tcp import TCPServerProtocol
from lib.networking.udp import UDPServerProtocol
from lib.networking.mixins import TCP
from lib.networking.ssl import ServerSideSSL
from lib.conf import ConfigurationException


class BaseAsyncioServer(BaseServer):
    default_protocol_cls = None

    @classmethod
    def from_config(cls, *args, cp=None, logger_name=None, **kwargs):
        logger = Logger(logger_name or cls.logger_name)
        protocol_cls = cls.default_protocol_cls.with_config(cp=cp, logger=logger)
        return super().from_config(*args, cp=cp, protocol_cls=protocol_cls, logger_name=logger_name, **kwargs)

    def __init__(self, *args, protocol_cls=None, **kwargs):
        self.protocol_cls = protocol_cls or self.default_protocol_cls
        super().__init__(*args, **kwargs)


class BaseTCPServerReceiver(BaseAsyncioServer):
    receiver_type = "TCP Server"

    async def get_server(self):
        raise NotImplementedError

    async def start_server(self):
        self.server = await self.get_server()

        async with self.server:
            self.print_listening_message(self.server.sockets)
            await self.server.serve_forever()

    async def stop_server(self):
        if self.server:
            self.server.close()


class TCPServerReceiver(TCP, BaseTCPServerReceiver):
    configurable = BaseTCPServerReceiver.configurable.copy()
    configurable.update(TCP.configurable)
    default_protocol_cls = TCPServerProtocol
    ssl_cls = ServerSideSSL
    ssl_section_name = 'SSLServer'

    async def get_server(self):
        return await asyncio.get_event_loop().create_server(self.protocol_cls,
            self.host, self.port, ssl=self.ssl, ssl_handshake_timeout=self.ssl_handshake_timeout)


class UDPServerReceiver(BaseAsyncioServer):
    receiver_type = "UDP Server"
    transport = None
    protocol = None
    default_protocol_cls = UDPServerProtocol
    configurable = ChainMap(BaseAsyncioServer.configurable, {
        {'expiryminutes': int}
    })

    def __init__(self, *args, expiryminutes=30, **kwargs):
        super(UDPServerReceiver, self).__init__(*args, **kwargs)
        self.expiry_minutes = expiryminutes
        self.start_event = asyncio.Event()

    async def start_server(self):
        loop = asyncio.get_event_loop()
        if loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            partial(self.protocol_cls, self.manager), local_addr=(self.host, self.port))
        self.print_listening_message([self.transport.get_extra_info('socket')])
        self.start_event.set()
        await self.protocol.check_senders_expired(self.expiry_minutes)

    async def stop_server(self):
        if self.transport:
            self.transport.close()

    async def started(self):
        await self.start_event.wait()

    async def stopped(self):
        if self.transport and self.transport.is_closing():
            await self.protocol.wait_closed()
