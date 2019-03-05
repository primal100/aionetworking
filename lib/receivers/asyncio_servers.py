import asyncio
from functools import partial

from .base import BaseServer
from lib.networking.asyncio_protocols import TCPServerProtocol, UDPServerProtocol
from lib.networking.mixins import TCP
from lib.networking.ssl import ServerSideSSL
from lib.conf import ConfigurationException


class BaseAsyncioServer(BaseServer):
    protocol_cls = None

    @classmethod
    def from_config(cls, *args, cp=None, config=None, **kwargs):
        instance = super().from_config(*args, cp=cp, config=config, **kwargs)
        instance.protocol_cls = cls.protocol_cls.with_config(cp=cp, logger=instance.logger)
        return instance


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
    protocol_cls = TCPServerProtocol
    ssl_cls = ServerSideSSL
    ssl_section_name = 'SSLServer'

    async def get_server(self):
        return await asyncio.get_event_loop().create_server(partial(self.protocol_cls, self.manager),
            self.host, self.port, ssl=self.ssl, ssl_handshake_timeout=self.ssl_handshake_timeout)


class UDPServerReceiver(BaseAsyncioServer):
    receiver_type = "UDP Server"
    transport = None
    protocol = None
    protocol_cls = UDPServerProtocol
    configurable = BaseAsyncioServer.configurable.copy()
    configurable.update({'expiryminutes': int})

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
