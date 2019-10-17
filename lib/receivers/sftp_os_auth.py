from dataclasses import dataclass
from lib.compatibility_os import authenticate, authentication_type
from lib.networking.protocol_factories import BaseProtocolFactory
from .sftp import SSHServer, SFTPServer


@dataclass
class SSHServerOSAuth(SSHServer):

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.debug('Attempting login with %s', authentication_type)
        return authenticate(username, password)


@dataclass
class SFTPOSAuthProtocolFactory(BaseProtocolFactory):
    full_name = 'SFTP Server'
    peer_prefix = 'sftp'
    connection_cls = SSHServerOSAuth


@dataclass
class SFTPServerOSAuth(SFTPServer):
    protocol_factory = SFTPOSAuthProtocolFactory

