import asyncssh
import asyncio
import datetime
import logging
from functools import partial
from passlib.hash import pbkdf2_sha256

from lib import settings
from lib.wrappers.futures import NamedFutures
from lib.networking.asyncio_protocols import TCPServerProtocol
from .asyncio_servers import BaseTCPServerReceiver
from .exceptions import ServerException

from typing import Mapping
from pathlib import Path


class SFTPFactory(asyncssh.SFTPServer):
    logger_name: str = 'receiver'
    configurable = {'chroot': bool,
                    'baseuploaddir': Path,
                    'removetmpfiles': bool,
                    'orderbyfileopen': bool}

    @classmethod
    def with_config(cls, logger, cp=None, **kwargs):
        config = cp.section_as_dict('Receiver', **cls.configurable)
        logger.debug(f'Found config for SFTP Factory: {config}')
        config.update(**kwargs)
        order_by_file_open = config.pop('orderbyfileopen', False)
        if order_by_file_open:
            return partial(OrderedSFTPFactory, logger, **config)
        return partial(cls, logger=logger, **config)

    def __init__(self, conn, baseuploaddir: Path = settings.HOME.joinpath('sftp'), chroot=True,
                 removetmpfiles=False, logger=None):
        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger(self.logger_name)
        self.connection_protocol = conn._owner
        if chroot:
            root = baseuploaddir.joinpath(conn.get_extra_info('username'))
            root.mkdir(parents=True, exist_ok=True)
            super().__init__(conn, chroot=root)
        else:
            super().__init__(conn)
        self.remove_tmp_files = removetmpfiles
        self.conn = conn

    def handle_file(self, name, data):
        path = Path(name)
        timestamp = datetime.datetime.fromtimestamp(path.stat().st_ctime)
        self.connection_protocol.on_data_received(data, timestamp=timestamp)
        if self.remove_tmp_files:
            path.unlink()
            self.logger.debug('File %s removed', path)

    def read_file(self, file_obj):
        path = Path(file_obj.name)
        mode = 'rb' if file_obj.mode == 'wb' else 'r'
        with path.open(mode=mode) as f:
            data = f.read()
        return data

    def on_close(self, file_obj, data):
        self.handle_file(file_obj.name, data)

    def close(self, file_obj):
        super(SFTPFactory, self).close(file_obj)
        self.logger.debug('File upload complete: %s', file_obj.name)
        data = self.read_file(file_obj)
        self.on_close(file_obj, data)


class OrderedSFTPFactory(SFTPFactory):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.futures = NamedFutures()
        self.process_task = asyncio.create_task(self.process_files())

    async def process_files(self):
        name, result = await self.futures.wait_one()
        self.handle_file(name, result)
        await self.process_files()

    def open(self, *args, **kwargs):
        file_obj = super(OrderedSFTPFactory, self).open(*args, **kwargs)
        self.futures.new(file_obj.name)
        return file_obj

    def on_close(self, file_obj, data):
        self.futures.set_result(file_obj.name, data)


class SSHServer(TCPServerProtocol, asyncssh.SSHServer):

    def __init__(self, manager, logins=None, public_key_auth_supported=False, logger=None):
        super(SSHServer, self).__init__(manager, logger=logger)
        self._public_key_auth_supported = public_key_auth_supported
        self.logins = logins

    def send(self, msg):
        raise ServerException('Unable to send messages with this receiver')


class SSHServerPswPublicAuth(SSHServer):
    hash_algorithm = pbkdf2_sha256

    def get_password(self, username: str) -> str:
        return self.logins.get(username, raw=True)

    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return bool(self.logins)

    def hash_password(self, password: str) -> str:
        return self.hash_algorithm.hash(password)

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.debug('Beginning password authentication for user %s', username)
        user_allowed = username in self.logins
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
        return self._public_key_auth_supported


class SFTPServer(BaseTCPServerReceiver):
    protocol_cls = SSHServer
    factory = SFTPFactory
    receiver_type = 'SFTP Server'
    logger_name = 'receiver'

    @classmethod
    def from_config(cls, *args, cp=None, config=None, **kwargs):
        instance = super().from_config(*args, cp=cp, config=config, **kwargs)
        instance.factory = cls.factory.with_config(cp=cp, logger=instance.logger)
        return instance

    configurable = BaseTCPServerReceiver.configurable.copy()
    configurable.update({'sftploglevel': int, 'allowscp': bool, 'hostkey': Path,
                         'passphrase': str, 'authorizedkeys': Path})

    def __init__(self, manager, *args, port=asyncssh.connection._DEFAULT_PORT, sftploglevel=1,
                 allowscp: bool=False, hostkey: Path=(), passphrase: str = None,
                 authorizedkeys: Path=None, sftp_kwargs=None, **kwargs):
        asyncssh.logging.set_debug_level(sftploglevel)
        super(SFTPServer, self).__init__(manager, *args, port=port, **kwargs)
        self.sftp_kwargs = {
            'allow_scp': allowscp,
            'server_host_keys': hostkey,
            'passphrase': passphrase,
            'authorized_client_keys': str(authorizedkeys) if authorizedkeys else None
        }
        self.connection_kwargs = {'public_key_auth_supported': bool(authorizedkeys)}
        sftp_kwargs = sftp_kwargs or {}
        self.sftp_kwargs.update(sftp_kwargs)
        self.allow_scp = allowscp

    async def get_server(self):
        return await asyncssh.create_server(partial(self.protocol_cls, **self.connection_kwargs), self.host,
                                            self.port, sftp_factory=self.factory, **self.sftp_kwargs)


class SFTPServerPswPublicAuth(SFTPServer):
    protocol = SSHServerPswPublicAuth

    configurable = SFTPServer.configurable.copy()
    configurable.update({'logins': dict})

    def __init__(self, manager, logins: Mapping[str, str]=None, *args, **kwargs):
        super(SFTPServerPswPublicAuth, self).__init__(manager, *args, **kwargs)
        self.connection_kwargs['logins'] = logins


