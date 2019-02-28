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
    configurable = {}

    @classmethod
    def from_config(cls, manager: BaseMessageManager, cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Receiver', **cls.configurable)
        config['logger_name'] = cp.logger_name
        logger = logging.getLogger(cp.logger_name)
        logger.debug('Found configuration for %s:%s', cls.receiver_type, config)
        config.update(kwargs)
        return cls(manager, **config)

    def __init__(self, manager, logger_name: str = 'receiver'):
        self.logger = logging.getLogger(logger_name)
        self.manager = manager

    async def started(self):
        return True

    async def stopped(self):
        return True

    async def start(self):
        try:
            await self.run()
        except asyncio.CancelledError:
            self.logger.debug('Receiver task cancelled')
            await self.close()

    async def close(self):
        pass

    async def run(self):
        raise NotImplementedError

    async def wait_stopped(self):
        pass


class BaseServer(BaseReceiver):
    configurable = BaseReceiver.configurable.copy()
    configurable.update({
        'host': str,
        'port': int,
        'ssl': bool,
        'sslcert': Path,
        'sslkey': Path,
        'sslkeypassword': str,
        'clientcertfile': Path,
        'clientcertsdir': Path,
        'clientcertsdata': str,
        'certrequired': bool,
        'hostnamecheck': bool,
        'sslhandshaketimeout': int,
    })
    ssl_allowed: bool = False
    receiver_type = 'Server'
    server = None

    def __init__(self, *args, host: str = '0.0.0.0', port: int=4000, ssl=False, sslcert: Optional[Path] = None,
                 sslkey: Optional[Path] = None, sslkeypassword: str = None, clientcertfile: Path = None, clientcertsdir: Path = None,
                 clientcertsdata: str = None, certrequired: bool = False, hostnamecheck: bool = False,
                 sslhandshaketimeout: int=None, **kwargs):
        super(BaseServer, self).__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.ssl_handshake_timeout = sslhandshaketimeout
        self.listening_on = '%s:%s' % (self.host, self.port)
        if self.ssl_allowed:
            self.ssl_context = self.manage_ssl_params(ssl, sslcert, sslkey, sslkeypassword, clientcertfile,
                                                      clientcertsdir, clientcertsdata, certrequired, hostnamecheck)
        elif ssl:
            self.logger.error('SSL is not supported for %s', self.receiver_type)
            raise ConfigurationException('SSL is not supported for' + self.receiver_type)
        else:
            self.ssl_context = None

    def manage_ssl_params(self, context, cert: Path, key: Path, sslkeypassword: str, cafile: Path, capath: Path, cadata: str,
                          certrequired: bool, hostnamecheck: bool) -> Optional[ssl.SSLContext]:
        if context:
            self.logger.info("Setting up SSL")
            if context is True:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                if cert and key:
                    self.logger.info("Using SSL Cert: %s", cert)
                    context.load_cert_chain(str(cert), str(key), password=sslkeypassword)

                context.verify_mode = ssl.CERT_REQUIRED if certrequired else ssl.CERT_NONE
                context.check_hostname = hostnamecheck

                if context.verify_mode != ssl.CERT_NONE:
                    if cafile or capath or cadata:
                        locations = {'cafile': str(cafile) if cafile else None,
                                     'capath': str(capath) if capath else None,
                                     'cadata': cadata}
                        context.load_verify_locations(**locations)
                        self.logger.info("Verifying SSL certs with: %s", locations)
                    else:
                        context.load_default_certs(ssl.Purpose.CLIENT_AUTH)
                        self.logger.info("Verifying SSL certs with: %s", ssl.get_default_verify_paths())
            self.logger.info("SSL Context loaded")
            return context
        else:
            self.logger.info("SSL is not enabled")
            return None

    def print_listening_message(self, sockets):
        for socket in sockets:
            sock_name = socket.getsockname()
            listening_on = ':'.join([str(v) for v in sock_name])
            print('Serving %s on %s' % (self.receiver_type, listening_on))

    async def close(self):
        self.logger.info('Stopping %s running at %s', self.receiver_type, self.listening_on)
        await self.stop_server()
        self.logger.info('%s stopped', self.receiver_type)

    async def run(self):
        self.logger.info('Starting %s on %s', self.receiver_type, self.listening_on)
        await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError

    async def started(self):
        while not self.server or not self.server.is_serving():
            await asyncio.sleep(0.01)

    async def stopped(self):
        if self.server:
            await self.server.wait_closed()
