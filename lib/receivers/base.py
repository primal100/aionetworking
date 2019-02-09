import asyncio
import ssl

from lib import settings
from lib.conf import ConfigurationException

from typing import TYPE_CHECKING, Optional
from pathlib import Path

if TYPE_CHECKING:
    from lib.messagemanagers.base import BaseMessageManager
else:
    BaseMessageManager = None

logger = settings.get_logger('main')


class ServerException(Exception):
    pass


class BaseReceiver:
    receiver_type: str = ''
    ssl_allowed: bool = False

    configurable = {
        'ssl_enabled': bool,
        'ssl_cert': Path,
        'ssl_key': Path,
    }

    @classmethod
    def from_config(cls, manager: BaseMessageManager, status_change=None, cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Receiver', **cls.configurable)
        logger.debug('Found configuration for %s:%s', cls.receiver_type, config)
        config.update(kwargs)
        return cls(manager, status_change=status_change, **config)

    def __init__(self, manager, status_change=None, ssl_enabled: bool = False, ssl_cert: Optional[Path] = None,
                 ssl_key: Optional[Path] = None):
        self.manager = manager
        self.status_change = status_change
        if self.ssl_allowed:
            self.ssl_context = self.manage_ssl_params(ssl_enabled, ssl_cert, ssl_key)
        elif ssl_enabled:
            logger.error('SSL is not supported for %s', self.receiver_type)
            raise ConfigurationException('SSL is not supported for' + self.receiver_type)
        else:
            self.ssl_context = None

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

    """async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug('Exiting %s receiver', self.receiver_type)
        if exc_type:
            error = traceback.format_exception(exc_type, exc_val, exc_tb)
            logger.error('\n'.join(error))
        await self.close()
        logger.debug('Exited from %s', self.receiver_type)"""

    async def started(self):
        return True

    async def stopped(self):
        return True

    async def start(self):
        try:
            await self.run()
        except asyncio.CancelledError:
            logger.debug('Receiver task cancelled')
            await self.close()

    async def close(self):
        pass

    async def run(self):
        raise NotImplementedError

    async def stop(self):
        raise NotImplementedError

    async def wait_stopped(self):
        pass


class BaseServer(BaseReceiver):
    configurable = BaseReceiver.configurable.copy()
    configurable.update({'host': str, 'port': int})
    receiver_type = 'Server'
    server = None

    def __init__(self, *args, host: str = '0.0.0.0', port: int=4000, **kwargs):
        super(BaseServer, self).__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.listening_on = '%s:%s' % (self.host, self.port)

    def print_listening_message(self, sockets):
        for socket in sockets:
            sock_name = socket.getsockname()
            listening_on = ':'.join([str(v) for v in sock_name])
            print('Serving %s on %s' % (self.receiver_type, listening_on))

    async def close(self):
        logger.info('Stopping %s running at %s', self.receiver_type,  self.listening_on)
        await self.stop_server()
        logger.info('%s stopped', self.receiver_type)

    async def run(self):
        logger.info('Starting %s on %s', self.receiver_type, self.listening_on)
        await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError

    async def started(self):
        if not self.server or not self.server.is_serving():
            await asyncio.sleep(0.01)

    async def stopped(self):
        if self.server:
            await self.server.wait_closed()
