import asyncssh
import logging
from passlib.hash import pbkdf2_sha256

from lib import settings
from .asyncio_servers import TCPServerReceiver

from typing import Mapping
from pathlib import Path


class SFTPFactory(asyncssh.SFTPServer):
    logger_name = 'receiver'

    def __init__(self, conn, receiver):
        self.logger = logging.getLogger(self.logger_name)
        #receiver.check_sender
        root = receiver.base_upload_dir.joinpath(conn.get_extra_info('username'))
        root.mkdir(parents=True, exist_ok=True)
        super().__init__(conn, chroot=root)
        self.receiver = receiver
        self.manager = receiver.manager
        self.conn = conn

    def connection_made(self):
        self.logger.debug('Connection made')
        print('connection made')

    def close(self, file_obj):
        super(SFTPFactory, self).close(file_obj)
        print('File upload complete')
        # self.on_data_received('username', data)


class SSHServer(asyncssh.SSHServer):
    logger_name = 'receiver'

    def __init__(self, receiver, logger=None):
        self.receiver = receiver
        if logger:
            self.logger = logger
        else:
            self.logger = logger.getLogger(self.logger_name)


class SSHServerPswAuth(SSHServer):
    hash_algorithm = pbkdf2_sha256

    def get_password(self, username: str) -> str:
        return self.receiver.logins.get(username, raw=True)

    def begin_auth(self, username: str) -> bool:
        self.logger.debug('Beginning password authentication for user %s', username)
        user_allowed = username in self.receiver.logins
        if not user_allowed:
            self.logger.info('SFTP User %s does not exist', username)
        return user_allowed

    def password_auth_supported(self) -> bool:
        return True

    def hash_password(self, password: str) -> str:
        return self.hash_algorithm.hash(password)

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.debug('Authorizing SFTP user %s', username)
        pw_hash = self.get_password(username)
        authorized = self.hash_algorithm.verify(password, pw_hash)
        if not authorized:
            self.logger.info('SFTP Login with user %s failed', username)
        else:
            self.logger.debug('SFTP User % successfully authorized', username)
        return authorized


class SFTPServer(TCPServerReceiver):
    factory = SFTPFactory
    protocol = SSHServer
    receiver_type = 'SFTP Server'
    logger_name = 'receiver'

    configurable = TCPServerReceiver.configurable.copy()
    configurable.update({'sftploglevel': int, 'allowscp': bool, 'baseuploaddir': Path, 'hostkey': Path, 'gsshost': str})

    def __init__(self, manager, *args, allowscp: bool=False, sftploglevel=1, hostkey='', gsshost=(),
                 baseuploaddir: Path = settings.HOME.joinpath('sftp'), **kwargs):
        asyncssh.logging.set_debug_level(sftploglevel)
        super(TCPServerReceiver, self).__init__(manager, *args, **kwargs)
        self.sftp_kwargs = {
            'server_host_keys': [hostkey] if hostkey else None,
            'gss_host': gsshost,
            'allow_scp': allowscp
        }
        self.allow_scp = allowscp
        self.base_upload_dir = baseuploaddir
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    async def get_server(self):
        return await asyncssh.create_server(lambda :self.protocol(self, logger=self.logger), self.host, self.port,
                                            sftp_factory=lambda conn: self.factory(conn, self), **self.sftp_kwargs)


class SFTPServerPswAuth(SFTPServer):
    protocol = SSHServerPswAuth

    configurable = SFTPServer.configurable.copy()
    configurable.update({'logins': dict})

    def __init__(self, manager, logins: Mapping[str, str], *args, **kwargs):
        self.logins = logins
        super(SFTPServerPswAuth, self).__init__(manager, *args, **kwargs)


