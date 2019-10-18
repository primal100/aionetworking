from dataclasses import dataclass
from lib.compatibility_os import authenticate, authentication_type
from lib.networking.protocol_factories import BaseProtocolFactory
from .sftp import BaseSFTPServerPswAuth


@dataclass
class SFTPServerOSAuthProtocol(BaseSFTPServerPswAuth):

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.debug('Attempting login with %s', authentication_type)
        return authenticate(username, password)


@dataclass
class SFTPOSAuthProtocolFactory(BaseProtocolFactory):
    full_name = 'SFTP Server'
    peer_prefix = 'sftp'
    connection_cls = SFTPServerOSAuthProtocol


