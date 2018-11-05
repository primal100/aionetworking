import asyncio
import ssl
import logging
import datetime

import settings
from lib.conf import ConfigurationException

from typing import TYPE_CHECKING, Optional, Sequence, Mapping, AnyStr
from pathlib import Path

if TYPE_CHECKING:
    from lib.messagemanagers.base import BaseMessageManager
else:
    BaseMessageManager = None

logger = logging.getLogger(settings.LOGGER_NAME)
data_logger = logging.getLogger(settings.RAWDATA_LOGGER_NAME)


class ServerException(Exception):
    pass


class MessageFromNotAuthorizedHost(Exception):
    pass


def raise_message_from_not_authorized_host(sender, allowed_senders):
    msg = "Received message from unauthorized host %s. Authorized hosts are: %s"
    args = (sender, allowed_senders)
    logger.error(msg, *args)
    raise MessageFromNotAuthorizedHost(msg % args)


class BaseReceiver:
    receiver_type: str = ''
    ssl_allowed: bool = False

    configurable = {
        'ssl_enabled': bool,
        'ssl_cert': Path,
        'ssl_key': Path,
        'allowed_senders': tuple,
        'aliases': dict,
        'generate_timestamp': bool,
        'multiprocess': bool
    }

    @classmethod
    def from_config(cls, manager: BaseMessageManager, status_change=None, **kwargs):
        config = settings.CONFIG.section_as_dict('Receiver', **cls.configurable)
        logger.debug('Found configuration for %s:%s', cls.receiver_type, config)
        config.update(kwargs)
        return cls(manager, status_change=status_change, **config)

    def __init__(self, queue, status_change=None, ssl_enabled: bool=False, ssl_cert: Optional[Path]=None,
                 ssl_key: Optional[Path]=None, allowed_senders: Sequence=(), aliases: Mapping=None,
                 generate_timestamp: bool=False):

        self.queue = queue
        self.status_change = status_change
        self.generate_timestamp = generate_timestamp
        if self.ssl_allowed:
            self.ssl_context = self.manage_ssl_params(ssl_enabled, ssl_cert, ssl_key)
        elif ssl_enabled:
            logger.error('SSL is not supported for %s', self.receiver_type)
            raise ConfigurationException('SSL is not supported for' + self.receiver_type)
        else:
            self.ssl_context = None
        self.allowed_senders = allowed_senders
        self.aliases = aliases or {}

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

    def handle_message(self, sender: str, data: AnyStr):
        logger.debug("Received msg from %s", sender)
        data_logger.debug(data)

        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp: %s', timestamp)
        else:
            timestamp = None
        logger.debug('Adding message to queue')
        self.add_to_queue(sender, data, timestamp)

    def add_to_queue(self, host: str, encoded: AnyStr, timestamp: datetime):
        asyncio.create_task(self.queue.put((host, encoded, timestamp)))

    def get_alias(self, sender: str):
        alias = self.aliases.get(sender, sender)
        if alias != sender:
            logger.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        if self.allowed_senders and other_ip not in self.allowed_senders:
            raise_message_from_not_authorized_host(other_ip, self.allowed_senders)
        if self.allowed_senders:
            logger.debug('Sender is in allowed senders')
        return self.get_alias(other_ip)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    def set_status_changed(self, change: str=''):
        if self.status_change:
            self.status_change.set()
        logger.debug('Status change event has been set to indicate %s receiver was %s', self.receiver_type, change)

    async def cleanup(self):
        timeout = 10
        logger.info('Waiting %s seconds for queue to empty', timeout)
        #await self.queue.join()
        try:
            join_result = await asyncio.wait_for(self.queue.join(), timeout)
            logger.info('Queue empty')
        except asyncio.TimeoutError:
            logger.error('Queue did not empty')
        logging.info('%s application stopped', self.receiver_type)
        self.set_status_changed('stopped')

    async def stop(self):
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
        print('Serving %s on %s' % (self.receiver_type, listening_on))

    async def stop(self):
        logger.info('Stopping %s running at %s', self.receiver_type,  self.listening_on)
        await self.stop_server()
        logging.info('%s stopped', self.receiver_type)

    async def run(self):
        logger.info('Starting %s on %s', self.receiver_type, self.listening_on)
        return await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError
