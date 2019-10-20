import asyncio
from dataclasses import dataclass
from lib.compatibility_os import authenticate, authentication_type
from lib.networking.protocol_factories import BaseProtocolFactory
from .sftp import SFTPServerProtocol


@dataclass
class SFTPServerOSAuthProtocol(SFTPServerProtocol):

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        self.logger.info('Attemping SFTP %s login for user %s', authentication_type, password)
        authorized = await asyncio.get_event_loop().run_in_executor(None, authenticate, username, password)
        if authorized:
            self.logger.info('SFTP User % successfully logged in', username)
        else:
            self.logger.error('SFTP Login failed for user %s', username)
        return authorized


@dataclass
class SFTPOSAuthProtocolFactory(BaseProtocolFactory):
    full_name = 'SFTP Server'
    peer_prefix = 'sftp'
    connection_cls = SFTPServerOSAuthProtocol


