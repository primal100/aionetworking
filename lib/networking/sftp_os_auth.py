import asyncio
from dataclasses import dataclass
from lib.compatibility_os import authenticate, authentication_type
from lib.networking.protocol_factories import BaseProtocolFactory
from functools import partial
from .sftp import SFTPServerProtocol

from typing import Dict, Any


@dataclass
class SFTPServerOSAuthProtocol(SFTPServerProtocol):
    windows_domain: str = '.'
    unix_group: str = ''

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        self.logger.info('Attempting SFTP %s login for user %s', authentication_type, password)
        authorized = await asyncio.get_event_loop().run_in_executor(None,
                                                                    partial(authenticate,
                                                                            group=self.unix_group,
                                                                            domain=self.windows_domain),
                                                                    username, password)
        if authorized:
            self.logger.info('SFTP User % successfully logged in', username)
        else:
            self.logger.error('SFTP Login failed for user %s', username)
        return authorized


@dataclass
class SFTPOSAuthProtocolFactory(BaseProtocolFactory):
    peer_prefix = 'sftp'
    connection_cls = SFTPServerOSAuthProtocol
    windows_domain: str = '.'
    unix_group: str = ''

    def _additional_connection_kwargs(self) -> Dict[str, Any]:
        return {
            'unix_group': self.unix_group,
            'windows_domain': self.windows_domain
        }
