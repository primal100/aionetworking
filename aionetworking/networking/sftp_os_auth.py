import asyncio
from dataclasses import dataclass
from aionetworking.compatibility_os import authenticate, authentication_type
from aionetworking.networking.protocol_factories import BaseProtocolFactory
from functools import partial
from .sftp import SFTPServerProtocol

from typing import Dict, Any


@dataclass
class SFTPServerOSAuthProtocol(SFTPServerProtocol):
    windows_domain: str = '.'
    pam_service: str = 'sftplogin'

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        self.logger.info('Attempting SFTP %s login for user %s', authentication_type.lower(), username)
        authorized = await asyncio.get_event_loop().run_in_executor(None,
                                                                    partial(authenticate,
                                                                            pam_service=self.pam_service,
                                                                            domain=self.windows_domain),
                                                                    username, password)
        if authorized:
            self.logger.info('SFTP User %s successfully logged in', username)
        else:
            self.logger.error('SFTP Login failed for user %s', username)
        return authorized


@dataclass
class SFTPOSAuthProtocolFactory(BaseProtocolFactory):
    peer_prefix = 'sftp'
    connection_cls = SFTPServerOSAuthProtocol
    windows_domain: str = '.'
    pam_service: str = 'sftplogin'

    def _additional_connection_kwargs(self) -> Dict[str, Any]:
        return {
            'pam_service': self.pam_service,
            'windows_domain': self.windows_domain
        }
