import asyncssh
import logging
from passlib.hash import pbkdf2_sha256

from lib import settings
from lib.connection_protocols.asyncio_protocols import TCPServerProtocol
from .asyncio_servers import TCPServerReceiver
from .exceptions import ServerException

from typing import Mapping
from pathlib import Path


class SFTPFactory(asyncssh.SFTPServer):
    logger_name = 'receiver'

    def __init__(self, conn, receiver):
        self.logger = logging.getLogger(self.logger_name)
        self.connection_protocol = conn._owner
        if receiver.chroot:
            root = receiver.base_upload_dir.joinpath(conn.get_extra_info('username'))
            root.mkdir(parents=True, exist_ok=True)
            super().__init__(conn, chroot=root)
        else:
            super().__init__(conn)
        self.receiver = receiver
        self.manager = receiver.manager
        self.conn = conn
        self.remove_after_processing = receiver.remove_after_processing

    def close(self, file_obj):
        super(SFTPFactory, self).close(file_obj)
        mode = 'rb' if file_obj.mode == 'wb' else 'r'
        path = Path(file_obj.name)
        self.logger.debug('File upload complete: %s', path)
        with path.open(mode=mode) as f:
            data = f.read()
        self.connection_protocol.data_received(data)
        if self.remove_after_processing:
            path.unlink()
            self.logger.debug('File %s removed', path)


class SSHServer(TCPServerProtocol, asyncssh.SSHServer):
    logger_name = 'receiver'

    def __init__(self, receiver, logger=None):
        super(SSHServer, self).__init__(receiver.manager, logger_name=self.logger_name)
        self.receiver = receiver
        if logger:
            self.logger = logger
        else:
            self.logger = logger.getLogger(self.logger_name)

    def send(self, msg):
        raise ServerException('Unable to send messages with this receiver')


class SSHServerPswPublicAuth(SSHServer):
    hash_algorithm = pbkdf2_sha256

    def get_password(self, username: str) -> str:
        return self.receiver.logins.get(username, raw=True)

    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return bool(self.receiver.logins)

    def hash_password(self, password: str) -> str:
        return self.hash_algorithm.hash(password)

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.debug('Beginning password authentication for user %s', username)
        user_allowed = username in self.receiver.logins
        if not user_allowed:
            self.logger.info('SFTP User %s does not exist', username)
            return False
        self.logger.debug('Authorizing SFTP user %s', username)
        pw_hash = self.get_password(username)
        authorized = self.hash_algorithm.verify(password, pw_hash)
        if not authorized:
            self.logger.info('SFTP Login with user %s failed', username)
        else:
            self.logger.debug('SFTP User % successfully authorized', username)
        return authorized

    def public_key_auth_supported(self):
        return self.receiver.public_key_auth_supported


class SFTPServer(TCPServerReceiver):
    factory = SFTPFactory
    protocol = SSHServer
    receiver_type = 'SFTP Server'
    logger_name = 'receiver'

    configurable = TCPServerReceiver.configurable.copy()
    configurable.update({'chroot': bool, 'sftploglevel': int, 'allowscp': bool,
                         'baseuploaddir': Path, 'hostkey': Path, 'removeafterprocessing': bool, 'passphrase': str,
                         'authorizedkeys': Path})

    def __init__(self, manager, *args, port=asyncssh.connection._DEFAULT_PORT, chroot: bool=True, sftploglevel=1,
                 baseuploaddir: Path = settings.HOME.joinpath('sftp'), remove_after_processing:bool = True,
                 allowscp: bool=False, hostkey: Path=(), passphrase: str = None, authorizedkeys: Path=None,
                 sftp_kwargs=None, **kwargs):
        asyncssh.logging.set_debug_level(sftploglevel)
        self.chroot = chroot
        super(TCPServerReceiver, self).__init__(manager, *args, port=port, **kwargs)
        self.sftp_kwargs = {
            'allow_scp': allowscp,
            'server_host_keys': hostkey,
            'passphrase': passphrase,
            'authorized_client_keys': str(authorizedkeys) if authorizedkeys else None
        }
        self.public_key_auth_supported = bool(authorizedkeys)
        sftp_kwargs = sftp_kwargs or {}
        self.sftp_kwargs.update(sftp_kwargs)
        self.allow_scp = allowscp
        self.base_upload_dir = baseuploaddir
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)
        self.remove_after_processing = remove_after_processing

    async def get_server(self):
        return await asyncssh.create_server(lambda: self.protocol(self, logger=self.logger), self.host, self.port,
                                            sftp_factory=lambda conn: self.factory(conn, self), **self.sftp_kwargs)


class SFTPServerPswPublicAuth(SFTPServer):
    protocol = SSHServerPswPublicAuth

    configurable = SFTPServer.configurable.copy()
    configurable.update({'logins': dict})

    def __init__(self, manager, logins: Mapping[str, str]=None, *args, **kwargs):
        self.logins = logins
        super(SFTPServerPswPublicAuth, self).__init__(manager, *args, **kwargs)


