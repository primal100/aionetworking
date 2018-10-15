import asyncio
import logging

logger = logging.getLogger()


class TCPClient:
    writer = None

    def __init__(self, msg_cls, host='127.0.0.1', port=4001, loop=None):
        self.msg_cls = msg_cls
        self.loop = loop or asyncio.get_event_loop()
        self.host = '10.166.1.71'
        self.port = port
        self.loop.create_task(self.start())

    async def start(self):
        logger.info("Opening TCP client connection to %s:%s" % (self.host, self.port))
        reader, self.writer = await asyncio.open_connection(self.host, self.port, loop=self.loop)
        logger.info('Connected')

    async def send_msg(self, msg_encoded):
        logger.debug("Sending message to %s:%s" % (self.host, self.port))
        logger.debug(msg_encoded)
        self.writer.write(msg_encoded)

    async def encode_and_send_msg(self, msg_decoded):
        msg = self.msg_cls('127.0.0.1', decoded=msg_decoded)
        await self.send_msg(msg.encoded)

    def close(self):
        logger.debug("Closing connection to %s:%s" % (self.host, self.port))
        self.writer.close()


class UDPClientProtocol:
    pass


class UDPClient(TCPClient):
    transport = None

    async def start(self):
        logger.debug("Opening UDP connection to %s:%s" % (self.host, self.port))
        self.transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: UDPClientProtocol(),
            remote_addr=(self.host, self.port))

    async def send_msg(self, msg_encoded):
        logger.debug("Sending message to %s:%s" % (self.host, self.port))
        logger.debug(msg.encoded)
        self.transport.sendto(msg_encoded)

    def close(self):
        logger.debug("Closing connection to %s:%s" % (self.host, self.port))
        self.transport.close()