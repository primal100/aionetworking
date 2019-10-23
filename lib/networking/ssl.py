from __future__ import annotations

from ssl import SSLContext, Purpose, CERT_REQUIRED, CERT_NONE, PROTOCOL_TLS, get_default_verify_paths
from lib.conf.logging import Logger, logger_cv
from lib.compatibility import Protocol

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class BaseSSLContext(Protocol):
    purpose = None
    logger: Logger = field(default_factory=logger_cv.get)
    ssl: bool = False
    cert: Path = None
    key: Path = None
    key_password: str = None
    cafile: Path = None
    capath: Path = None
    cadata: str = None
    cert_required: bool = False
    check_hostname: bool = False

    def set_logger(self, logger: Logger) -> None:
        self.logger = logger

    @property
    def context(self) -> Optional[SSLContext]:
        if self.ssl:
            self.logger.info("Setting up SSL")
            context = SSLContext(PROTOCOL_TLS)
            if self.cert and self.key:
                self.logger.info("Using SSL Cert: %s", self.cert)
                context.load_cert_chain(str(self.cert), str(self.key), password=self.key_password)
            context.verify_mode = CERT_REQUIRED if self.cert_required else CERT_NONE
            context.check_hostname = self.check_hostname

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
        return None


@dataclass
class ServerSideSSL(BaseSSLContext):
    purpose = Purpose.CLIENT_AUTH


@dataclass
class ClientSideSSL(BaseSSLContext):
    purpose = Purpose.SERVER_AUTH

