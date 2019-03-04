import asyncio

from .base import BaseServer
from lib.networking.asyncio_protocols import TCPServerProtocol, UDPServerProtocol
from lib.conf import ConfigurationException


class TCPServerReceiver(BaseServer):
    receiver_type = "TCP Server"
    ssl_allowed = True
    protocol_cls = TCPServerProtocol

    @classmethod
    def from_config(cls, *args, cp=None, **kwargs):
        instance = super().from_config(*args, cp=cp, **kwargs)
        cls.protocol_cls = cls.protocol_cls.set_config(cp=cp, logger=instance.logger)
        return instance

    async def get_server(self):
        return await asyncio.get_event_loop().create_server(
            lambda: self.protocol_cls(self.manager),
            self.host, self.port, ssl=self.ssl_context, ssl_handshake_timeout=self.ssl_handshake_timeout)

    async def start_server(self):
        self.server = await self.get_server()

        async with self.server:
            self.print_listening_message(self.server.sockets)
            await self.server.serve_forever()

    async def stop_server(self):
        if self.server:
            self.server.close()


class UDPServerReceiver(BaseServer):
    receiver_type = "UDP Server"
    transport = None
    protocol = None
    protocol_cls = UDPServerProtocol
    configurable = BaseServer.configurable.copy()
    configurable.update({'expiryminutes': int})

    @classmethod
    def from_config(cls, *args, cp=None, **kwargs):
        instance = super().from_config(*args, **kwargs)
        cls.protocol.set_config(cp=cp, logger=instance.logger)
        return instance

    def __init__(self, *args, expiryminutes=30, **kwargs):
        super(UDPServerReceiver, self).__init__(*args, **kwargs)
        self.expiry_minutes = expiryminutes

    async def start_server(self):
        loop = asyncio.get_event_loop()
        if loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: self.protocol_cls(self.manager),
            local_addr=(self.host, self.port))
        self.print_listening_message([self.transport.get_extra_info('socket')])
        await self.protocol.check_senders_expired(self.expiry_minutes)

    async def stop_server(self):
        if self.transport:
            self.transport.close()

    async def started(self):
        if not self.transport:
            await asyncio.sleep(0.01)

    async def stopped(self):
        if self.transport and self.transport.is_closing():
            await self.protocol.wait_closed()
