from ssl import SSLContext, Purpose, CERT_REQUIRED, CERT_NONE, PROTOCOL_TLS, get_default_verify_paths, \
    cert_time_to_seconds
import asyncio
import datetime
from aionetworking.logging.loggers import get_logger_receiver
from aionetworking.types.logging import LoggerType
from aionetworking.compatibility import Protocol, create_task, set_task_name, cached_property

from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field


try:
    import cryptography
    warn_if_expires_before_days_default = 7
except ImportError:
    warn_if_expires_before_days_default = None


def ssl_cert_time_to_datetime(timestamp: str) -> datetime.datetime:
    return datetime.datetime.utcfromtimestamp(cert_time_to_seconds(timestamp))


def check_ssl_cert_expired(expiry_time: datetime.datetime, warn_before_days: int) -> Optional[int]:
    expires_in = (expiry_time - datetime.datetime.now()).days
    if expires_in < warn_before_days:
        return expires_in
    return None


def check_peercert_expired(peercert: Dict[str, Any], warn_before_days: int) -> Tuple[datetime.datetime, Optional[int]]:
    expiry_time = ssl_cert_time_to_datetime(peercert['notAfter'])
    cert_expiry_in_days = check_ssl_cert_expired(expiry_time, warn_before_days)
    return expiry_time, cert_expiry_in_days


@dataclass
class BaseSSLContext(Protocol):
    purpose = None
    logger: LoggerType = field(default_factory=get_logger_receiver)
    ssl: bool = True
    cert: Path = None
    key: Path = None
    key_password: str = None
    cafile: Path = None
    capath: Path = None
    cadata: str = None
    cert_required: bool = False
    check_hostname: bool = True
    warn_if_expires_before_days: int = warn_if_expires_before_days_default
    _warn_expiry_task: asyncio.Task = field(default=None, init=False, compare=False)

    def set_logger(self, logger: LoggerType) -> None:
        self.logger = logger

    async def close(self) -> None:
        if self._warn_expiry_task and not self._warn_expiry_task.done():
            self._warn_expiry_task.cancel()

    async def check_cert_expiry(self):
        try:
            from .ssl_utils import load_cert_expiry_time
            cert_expiry_time = load_cert_expiry_time(self.cert)
            if cert_expiry_time:
                while True:
                    cert_expiry_days = check_ssl_cert_expired(cert_expiry_time, self.warn_if_expires_before_days)
                    if cert_expiry_days:
                        self.logger.warn_on_cert_expiry('Own', cert_expiry_days, cert_expiry_time)
                    await asyncio.sleep(86400)
        except ImportError:
            self.logger.warning(
                'Unable to check ssl cert validity. Install cryptography library to enable this or set warn_if_expires_before_days to 0')

    @cached_property
    def context(self) -> Optional[SSLContext]:
        if self.ssl:
            self.logger.info("Setting up SSL")
            context = SSLContext(PROTOCOL_TLS)
            if self.cert and self.key:
                self.logger.info("Using SSL Cert: %s", self.cert)
                context.load_cert_chain(str(self.cert), str(self.key), password=self.key_password)
                if self.warn_if_expires_before_days:
                    self._warn_expiry_task = create_task(self.check_cert_expiry())
                    set_task_name(self._warn_expiry_task, 'CheckSSLCertValidity')
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
    check_hostname: bool = False
    cert_required: bool = False


@dataclass
class ClientSideSSL(BaseSSLContext):
    purpose = Purpose.SERVER_AUTH
    check_hostname: bool = True
    cert_required: bool = True

