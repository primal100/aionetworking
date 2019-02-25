import asyncio
import logging
import ssl

from lib import settings
from lib.conf import ConfigurationException

from typing import TYPE_CHECKING, Optional
from pathlib import Path

if TYPE_CHECKING:
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseReceiver:
    receiver_type: str = ''
    ssl_allowed: bool = False
    configurable = {
        'ssl_enabled': bool,
        'ssl_cert': Path,
        'ssl_key': Path,
    }

    @classmethod
    def from_config(cls, manager: BaseMessageManager, cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Receiver', **cls.configurable)
        config['logger_name'] = cp.logger_name
        log = logging.getLogger(cp.logger_name)
        log.debug('Found configuration for %s:%s', cls.receiver_type, config)
        config.update(kwargs)
        return cls(manager, **config)

    def __init__(self, manager, ssl_enabled: bool = False, ssl_cert: Optional[Path] = None,
                 ssl_key: Optional[Path] = None, logger_name: str = 'receiver'):
        self.log = logging.getLogger(logger_name)
        self.manager = manager
        if self.ssl_allowed:
            self.ssl_context = self.manage_ssl_params(ssl_enabled, ssl_cert, ssl_key)
        elif ssl_enabled:
            self.log.error('SSL is not supported for %s', self.receiver_type)
            raise ConfigurationException('SSL is not supported for' + self.receiver_type)
        else:
            self.ssl_context = None

    def manage_ssl_params(self, enabled: bool, cert: Path, key: Path) -> Optional[ssl.SSLContext]:
        if enabled:
            if not cert or not key:
                raise ConfigurationException('SSLCert and SSLKey must be configured when SSL is enabled')
            self.log.info("Setting up SSL")
            self.log.info("Using SSL Cert: ", cert)
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(str(cert), str(key))
            self.log.info("SSL Context loaded")
            return ssl_context
        else:
            self.log.info("SSL is not enabled")
            return None

    async def started(self):
        return True

    async def stopped(self):
        return True

    async def start(self):
        try:
            await self.run()
        except asyncio.CancelledError:
            self.log.debug('Receiver task cancelled')
            await self.close()

    async def close(self):
        pass

    async def run(self):
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
        self.log.info('Stopping %s running at %s', self.receiver_type,  self.listening_on)
        await self.stop_server()
        self.log.info('%s stopped', self.receiver_type)

    async def run(self):
        self.log.info('Starting %s on %s', self.receiver_type, self.listening_on)
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
