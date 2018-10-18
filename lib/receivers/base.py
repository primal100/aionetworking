import ssl
import logging
import datetime
from lib.configuration import ConfigurationException
from lib import utils

logger = logging.getLogger('messageManager')


class ServerException(Exception):
    pass


class BaseReceiver:
    receiver_type = ""

    def __init__(self, manager, config, started_event=None, stopped_event=None):
        self.manager = manager
        self.config = config.receiver_config
        self.started_event = started_event
        self.stopped_event = stopped_event
        self.record = self.config.get('record', False)
        self.record_file = self.config.get('record_file', False)
        if self.record and not self.record_file:
            raise ConfigurationException('Please configure a record file when record is set to true')

        self.prev_message_time = None

    def manage_ssl_params(self):
        ssl_enabled = self.config.get('ssl', False)
        if ssl_enabled:
            ssl_cert = self.config.get('ssl_cert', '')
            ssl_key = self.config.get('ssl_key', '')
            if not ssl_cert or not ssl_key:
                raise ConfigurationException('SSLCert and SSLKey must be configured when SSL is enabled')
            logger.info("Setting up SSL")
            logger.info("Using SSL Cert: " + ssl_cert)
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(ssl_cert, ssl_key)
            logger.info("SSL Context loaded")
            return ssl_context
        else:
            logger.info("SSL is not enabled")
            return None

    def record_packet(self, msg, sender):
        logger.debug('Recording packet from %s' % sender)
        if self.prev_message_time:
            message_timedelta = (datetime.datetime.now() - self.prev_message_time).seconds
        else:
            message_timedelta = 0
        self.prev_message_time = datetime.datetime.now()
        data = utils.pack_recorded_packet(message_timedelta, sender, msg)
        with open(self.record_file, 'ab') as f:
            f.write(data)

    async def handle_message(self, sender, data):
        logger.debug("Received msg from " + sender)
        logger.debug(data)

        if self.record:
            self.record_packet(data, sender)

        await self.manager.manage_message(sender, data)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def stop(self):
        logger.info('Stopping %s application' % self.receiver_type)
        await self.close()
        await self.manager.close()
        logging.info('%s application stopped' % self.receiver_type)
        if self.stopped_event:
            self.stopped_event.set()
            logger.debug('Stopped event has been set')

    async def close(self):
        raise NotImplementedError

    async def run(self):
        raise NotImplementedError


class BaseServer(BaseReceiver):
    receiver_type = 'Server'
    default_host = '0.0.0.0'
    default_port = 4000

    def __init__(self, manager, config, **kwargs):
        super(BaseServer, self).__init__(manager, config, **kwargs)
        self.host = self.config.get('host', self.default_host)
        self.port = self.config.get('port', self.default_port)

    async def close(self):
        logger.info('Closing %s running at %s:%s' % (self.receiver_type, self.host, self.port))
        await self.stop_server()
        logging.info('%s closed' % self.receiver_type)

    async def run(self):
        logger.info('Starting %s on %s:%s' % (self.receiver_type, self.host, self.port))
        await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError
