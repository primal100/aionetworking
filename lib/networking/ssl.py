from ssl import SSLContext, Purpose, CERT_REQUIRED, CERT_NONE, PROTOCOL_TLS, get_default_verify_paths
from lib.conf.logging import Logger

from pydantic import BaseModel
from pydantic.main import DictStrAny
from pydantic.types import CallableGenerator

from pathlib import Path
from typing import Optional, Type, Union


class BaseSSLContext(BaseModel):
    context: SSLContext = None
    logger: Logger = None
    ssl: bool = False,
    cert: Path = None
    key: Path = None,
    key_password: str = None,
    cafile: Path = None,
    capath: Path = None,
    cadata: str = None,
    cert_required: bool = False,
    hostname_check: bool = False

    @classmethod
    def validate(cls: Type['BaseSSLContext'], value: Union['DictStrAny', 'BaseSSLContext']) -> Optional[SSLContext]:
        instance = super().validate(value)
        if instance.ssl and not instance.context:
            return instance.manage_ssl_params()
        elif instance.ssl and instance.context:
            return instance.context
        return None

    def manage_ssl_params(self, ) -> Optional[SSLContext]:
        self.logger.info("Setting up SSL")
        context = SSLContext(PROTOCOL_TLS)
        if self.cert and self.key:
            self.logger.info("Using SSL Cert: %s", self.cert)
            context.load_cert_chain(str(self.cert), str(self.key), password=self.key_password)
        context.verify_mode = CERT_REQUIRED if self.certrequired else CERT_NONE
        context.check_hostname = self.hostnamecheck

        if context.verify_mode != CERT_NONE:
             if self.cafile or self.capath or self.cadata:
                locations = {
                    'cafile': str(self.cafile) if self.cafile else None,
                    'capath': str(self.capath) if self.capath else None,
                    'cadata': self.cadata
                }
                context.load_verify_locations(**locations)
                self.logger.info("Verifying SSL certs with: %s", locations)
             else:
                context.load_default_certs(self.purpose)
                self.logger.info("Verifying SSL certs with: %s", get_default_verify_paths())
        self.logger.info("SSL Context loaded")
        return context


class ServerSideSSL(BaseSSLContext):
    purpose = Purpose.CLIENT_AUTH
    logger: Logger = Logger('receiver', {})


class ClientSideSSL(BaseSSLContext):
    purpose = Purpose.CLIENT_AUTH
    logger: Logger = Logger('sender', {})

