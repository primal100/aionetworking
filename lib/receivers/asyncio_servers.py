import asyncio
import ssl
import logging
import datetime
from lib.configuration import ConfigurationException
from lib import utils

logger = logging.getLogger()


class ServerException(Exception):
    pass


class TCPServer:
    default_host = '0.0.0.0'
    default_port = 4000

    def __init__(self, manager, config, loop=None):

        self.manager = manager
        self.config = config.receiver_config
        self.record = self.config.get('record', False)
        self.record_file = self.config.get('record_file', False)
        if self.record and not self.record_file:
            raise ConfigurationException('Please configure a record file when record is set to true')
        host = self.config.get('host', self.default_host)
        port = self.config.get('port', self.default_port)
        ssl_enabled = self.config.get('ssl', False)
        ssl_cert = self.config.get('ssl_cert', '')
        ssl_key = self.config.get('ssl_key', '')

        self.ssl_context = self.manage_ssl_params(ssl_enabled, ssl_cert, ssl_key)

        self.loop = loop or asyncio.get_event_loop()

        self.server = self.run(host, port)

        self.prev_message_time = None

    @staticmethod
    def manage_ssl_params(ssl_enabled, ssl_cert, ssl_key):
        if ssl_enabled:
            if not ssl_cert or not ssl_key:
                raise ConfigurationException('SSLCert and SSLKey must be configured when SSL is enabled')
            logger.info("Setting up SSL")
            logger.info("Using SSL Cert: " + sslcert)
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(ssl_cert, ssl_key)
            logger.info("SSL Context loaded")
            return ssl_context
        else:
            logger.info("SSL is not enabled")
            return None

    def record_packet(self, msg, sender):
        if self.prev_message_time:
            message_timedelta = (datetime.datetime.now() - self.prev_message_time).seconds
        else:
            message_timedelta = 0
        self.prev_message_time = datetime.datetime.now()
        data = utils.pack_recorded_packet(message_timedelta, sender, msg)
        with open(self.record_file, 'a+') as f:
            f.write(data)

    async def handle_packet(self, reader, writer):
        data = await reader.read(100)
        message = data.decode()
        sender = writer.get_extra_info('peername')
        if self.record:
            self.record(msg, sender)
        logger.debug("Received msg from " + sender)
        logger.debug(data)
        logger.debug(message)
        await self.manager.manage(sender, message)

    def close(self):
        logger.info('Closing server')
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        logging.info('Server closed')

    def run(self, host, port):
        logger.info('Starting TCP server on %s:%s' % (host, port))

        coro = asyncio.start_server(self.handle_packet, host, port, ssl=self.ssl_context, loop=self.loop)
        server = self.loop.run_until_complete(coro)

        logger.info('Server started')
        print('Serving TCP Server on {}'.format(server.sockets[0].getsockname()))

        return server


class UDPServerProtocol:
    default_port = 4001

    def __init__(self, server):
        self.server = server

    async def datagram_received(self, data, sender):
        message = data.decode()
        if self.server.record:
            self.server.record_packet(msg, sender)
        logger.debug("Received msg from " + sender)
        logger.debug(data)
        logger.debug(message)
        await self.server.manager.manage(sender, message)


class UDPServer(TCPServer):

    async def run(self, host, port):
        logger.info('Starting UDP server on %s:%s' % (host, port))
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: UDPServerProtocol(self),
            local_addr=(host, port))
        logger.info('Server started')
        print('Serving UDP Server on {}'.format(transport.sockets[0].getsockname()))
        return transport
