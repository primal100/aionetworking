import ssl
import logging
import datetime
from pathlib import Path
from typing import Optional

from lib import utils
from lib.conf import ConfigurationException
from lib.messagemanagers.base import BaseMessageManager
import definitions

logger = logging.getLogger(definitions.LOGGER_NAME)


class ServerException(Exception):
    pass


class BaseReceiver:
    receiver_type: str = ''
    ssl_allowed: bool = False

    configurable = {
        'record': bool,
        'record_file': Path,
        'ssl_enabled': bool,
        'ssl_cert': Path,
        'ssl_key': Path
    }

    @classmethod
    def from_config(cls, manager:BaseMessageManager, status_change=None, **kwargs):
        config = definitions.CONFIG.section_as_dict('Receiver', **cls.configurable)
        logger.debug('Found configuration for', cls.receiver_type, ':', config)
        config.update(kwargs)
        return cls(manager, status_change=status_change, **kwargs)

    def __init__(self, manager: BaseMessageManager, status_change=None, record: bool=False,
                 record_file: Path=None, ssl_enabled: bool=False, ssl_cert: Optional[Path]=None,
                 ssl_key: Optional[Path]=None):

        self.manager = manager
        self.status_change = status_change
        if self.ssl_allowed:
            self.ssl_context = self.manage_ssl_params(ssl_enabled, ssl_cert, ssl_key)
        elif ssl_enabled:
            logger.error('SSL is now supported for', self.receiver_type)
            raise ConfigurationException('SSL is now supported for' + self.receiver_type)
        else:
            self.ssl_context = None
        self.record = record
        self.record_file = record_file
        if self.record:
            if self.record_file:
                self.record_file.parent.mkdir(parents=True, exist_ok=True)
            else:
                logger.error('No record file configured although record is set to true')
                raise ConfigurationException('Please configure a record file when record is set to true')

        self.prev_message_time = None

    @staticmethod
    def manage_ssl_params(enabled: bool, cert: Path, key: Path) -> Optional[ssl.SSLContext]:
        if enabled:
            if not cert or not key:
                raise ConfigurationException('SSLCert and SSLKey must be configured when SSL is enabled')
            logger.info("Setting up SSL")
            logger.info("Using SSL Cert: ", cert)
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(str(cert), str(key))
            logger.info("SSL Context loaded")
            return ssl_context
        else:
            logger.info("SSL is not enabled")
            return None

    def record_packet(self, sender: str, msg: bytes):
        logger.debug('Recording packet from', sender)
        if self.prev_message_time:
            message_timedelta = (datetime.datetime.now() - self.prev_message_time).seconds
        else:
            message_timedelta = 0
        self.prev_message_time = datetime.datetime.now()
        data = utils.pack_recorded_packet(message_timedelta, sender, msg)
        with self.record_file.open('ab') as f:
            f.write(data)

    async def handle_message(self, sender: str, data: bytes):
        logger.debug("Received msg from ", sender)
        logger.debug(data)

        if self.record:
            self.record_packet(sender, data)

        await self.manager.manage_message(sender, data)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    def set_status_changed(self, change: str=''):
        if self.status_change:
            self.status_change.set()
        logger.debug('Status change event has been set to indicate', self.receiver_type, 'receiver was', change)

    async def stop(self):
        logger.info('Stopping', self.receiver_type, 'application')
        await self.close()
        await self.manager.close()
        logging.info(self.receiver_type, 'application stopped')
        self.set_status_changed('stopped')

    async def close(self):
        raise NotImplementedError

    async def run(self):
        raise NotImplementedError


class BaseServer(BaseReceiver):
    configurable = BaseReceiver.configurable.copy()
    configurable.update({'host': str, 'port': int})
    receiver_type = 'Server'
    server = None

    def __init__(self, *args, host: str='0.0.0.0', port: int=4000, **kwargs):
        super(BaseServer, self).__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.listening_on = '%s:%s' % (self.host, self.port)

    def print_listening_message(self, socket):
        sock_name = socket.getsockname()
        listening_on = ':'.join([str(v) for v in sock_name])
        print('Serving', self.receiver_type, 'on', listening_on)

    async def close(self):
        logger.info('Closing', self.receiver_type,  'running at', self.listening_on)
        await self.stop_server()
        logging.info(self.receiver_type, 'closed')

    async def run(self):
        logger.info('Starting', self.receiver_type, 'on', self.listening_on)
        await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError
