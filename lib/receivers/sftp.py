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
        print('connection made')

    def close(self, file_obj):
        super(SFTPFactory, self).close(file_obj)
        print('File upload complete')
        # self.on_data_received('username', data)


class SFTPFactoryPswAuth(SFTPFactory):
    hash_algorithm = pbkdf2_sha256

    def get_password(self, username: str) -> str:
        return self.receiver.logins[username]

    def begin_auth(self, username: str) -> bool:
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
    receiver_type = 'SFTP Server'
    logger_name = 'receiver'

    configurable = TCPServerReceiver.configurable.copy()
    configurable.update({'allowscp': bool, 'baseuploaddir': Path, 'hostkey': Path})

    def __init__(self, manager, *args, allowscp: bool=False, hostkey='',
                 baseuploaddir: Path = settings.HOME.joinpath('sftp'), **kwargs):
        super(TCPServerReceiver, self).__init__(manager, *args, **kwargs)
        #self.hostkeys = [hostkey]
        self.hostkeys = None
        self.allow_scp = allowscp
        self.base_upload_dir = baseuploaddir
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    async def get_server(self):
        return await asyncssh.listen(self.host, self.port, server_host_keys=self.hostkeys,
                                     sftp_factory=lambda conn: self.factory(conn, self),
                                     allow_scp=self.allow_scp)


class SFTPServerPswAuth(SFTPServer):
    factory = SFTPFactoryPswAuth

    configurable = SFTPServer.configurable.copy()
    configurable.update({'logins': dict})

    def __init__(self, manager, logins: Mapping[str, str], *args, **kwargs):
        self.logins = logins
        super(SFTPServerPswAuth, self).__init__(manager, *args, **kwargs)


