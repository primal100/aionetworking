import asyncio
from dataclasses import dataclass
from lib.compatibility_os import authenticate, authentication_type
from lib.conf.context import context_cv
from lib.networking.protocol_factories import BaseProtocolFactory
from functools import partial
from .sftp import SFTPServerProtocol


@dataclass
class SFTPServerOSAuthProtocol(SFTPServerProtocol):
    windows_domain: str = '.'
    unix_group: str = ''

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        self.logger.info('Attemping SFTP %s login for user %s', authentication_type, password)
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

    def _new_connection(self) -> SFTPServerOSAuthProtocol:
        context_cv.set(context_cv.get().copy())
        self.logger.debug('Creating new connection')
        return self.connection_cls(parent_name=self.full_name, peer_prefix=self.peer_prefix, action=self.action,
                                   preaction=self.preaction, requester=self.requester, dataformat=self.dataformat,
                                   pause_reading_on_buffer_size=self.pause_reading_on_buffer_size, logger=self.logger,
                                   windows_domain=self.windows_domain, unix_group=self.unix_group)