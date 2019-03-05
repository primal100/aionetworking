import ssl
import logging

from pathlib import Path
from typing import Optional


class BaseSSLManager:
    purpose: str = None
    logger_name: str = None
    configurable = {
        'ssl': bool,
        'cert': Path,
        'key': Path,
        'keypassword': str,
        'cafile': Path,
        'capath': Path,
        'cadata': str,
        'certrequired': bool,
        'hostnamecheck': bool}

    @classmethod
    def from_config(cls, section, cp=None, logger=None, **kwargs):
        if not logger:
            logger = logging.getLogger(cls.logger_name)
        from lib.settings import CONFIG
        config = cp or CONFIG
        config = config.section_as_dict(section, **cls.configurable)
        config.update(**kwargs)
        logger.debug(f'Found config for SSL context {section}: {config}')
        return cls(logger=logger, **config)

    @classmethod
    def get_context(cls, *args, **kwargs):
        return cls.from_config(*args, **kwargs).context

    def __init__(self, ssl: bool = False, cert: Path=None, key: Path=None, sslkeypassword: str=None, cafile: Path=None,
                 capath: Path = None, cadata: str = None, certrequired: bool=False, hostnamecheck: bool = False,
                 logger=None):
        if ssl:
            self.logger = logger
            if not logger:
                self.logger = logging.getLogger(self.logger_name)
            self.context = self.manage_ssl_params(cert, key, sslkeypassword, cafile, capath,
                        cadata, certrequired, hostnamecheck)
        else:
            self.context = None

    def manage_ssl_params(self, cert, key, sslkeypassword, cafile, capath, cadata, certrequired,
                          hostnamecheck) -> Optional[ssl.SSLContext]:
        self.logger.info("Setting up SSL")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        if cert and key:
            self.logger.info("Using SSL Cert: %s", cert)
            context.load_cert_chain(str(cert), str(key), password=sslkeypassword)
        context.verify_mode = ssl.CERT_REQUIRED if certrequired else ssl.CERT_NONE
        context.check_hostname = hostnamecheck

        if context.verify_mode != ssl.CERT_NONE:
             if cafile or capath or cadata:
                locations = {
                    'cafile': str(cafile) if cafile else None,
                    'capath': str(capath) if capath else None,
                    'cadata': cadata
                }
                context.load_verify_locations(**locations)
                self.logger.info("Verifying SSL certs with: %s", locations)
             else:
                context.load_default_certs(self.purpose)
                self.logger.info("Verifying SSL certs with: %s", ssl.get_default_verify_paths())
        self.logger.info("SSL Context loaded")
        return context


class ServerSideSSL(BaseSSLManager):
    purpose = ssl.Purpose.CLIENT_AUTH
    logger_name = 'receiver'


class ClientSideSSL(BaseSSLManager):
    purpose = ssl.Purpose.CLIENT_AUTH
    logger_name = 'sender'

