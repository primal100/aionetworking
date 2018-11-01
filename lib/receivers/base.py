import asyncio
import concurrent.futures
import ssl
import logging
import datetime

import definitions
import settings
from lib import utils
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
        'record': bool,
        'record_file': Path,
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

    def __init__(self, queue, status_change=None, record: bool=False,
                 record_file: Path=None, ssl_enabled: bool=False, ssl_cert: Optional[Path]=None,
                 ssl_key: Optional[Path]=None, allowed_senders: Sequence=(), aliases: Mapping=None,
                 generate_timestamp: bool=False):

        self.queue = None
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
        logger.debug('Recording packet from %s', sender)
        if self.prev_message_time:
            message_timedelta = (datetime.datetime.now() - self.prev_message_time).seconds
        else:
            message_timedelta = 0
        self.prev_message_time = datetime.datetime.now()
        data = utils.pack_recorded_packet(message_timedelta, sender, msg)
        with self.record_file.open('ab') as f:
            f.write(data)

    async def handle_message(self, sender: str, data: bytes):
        logger.debug("Received msg from %s", sender)
        data_logger.debug(data)

        if self.record:
            self.record_packet(sender, data)

        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp: %s', timestamp)
        else:
            timestamp = None
        logger.debug('Adding message from %s to queue', sender)
        await self.add_to_queue(sender, data, timestamp)

    async def add_to_queue(self, host: str, encoded: AnyStr, timestamp: datetime):
        self.queue.put((host, encoded, timestamp))

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
        await self.stop()

    def set_status_changed(self, change: str=''):
        if self.status_change:
            self.status_change.set()
        logger.debug('Status change event has been set to indicate %s receiver was %s', self.receiver_type, change)

    def join(self, timeout=10):
        self.queue.join()
        with self.queue.all_tasks_done:
            while self.queue.unfinished_tasks:
                return self.queue.all_tasks_done.wait(timeout=timeout)

    async def stop(self):
        logger.info('Stopping %s application', self.receiver_type)
        await self.close()
        timeout = 10
        logger.info('Waiting %s seconds for queue to empty', timeout)
        if self.join(timeout=timeout):
            logger.info('Queue empty. Cancelling task')
        else:
            logger.error('Queue did not empty. Cancelling task with messages in queue.')
        self.process_queue_task.cancel()
        logging.info('%s application stopped', self.receiver_type)
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
        print('Serving %s on %s' % (self.receiver_type, listening_on))

    async def close(self):
        logger.info('Closing %s running at %s', self.receiver_type,  self.listening_on)
        await self.stop_server()
        logging.info('%s closed', self.receiver_type)

    async def run(self):
        logger.info('Starting %s on %s', self.receiver_type, self.listening_on)
        await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError
