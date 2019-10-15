import asyncssh
import aiofiles.os
import asyncio
import datetime
from dataclasses import dataclass, field, InitVar
from functools import partial
from passlib.hash import pbkdf2_sha256

from lib import settings
from lib.wrappers.schedulers import TaskScheduler
from lib.networking.connections import NetworkConnectionProtocol
from lib.utils import aremove
from .base import BaseNetworkServer
from .exceptions import ServerException

from typing import Dict, Any, Optional, AnyStr, Union
from pathlib import Path


def create_queue_if_not_exists(conn):
    queue = conn.get_extra_info('file_queue')
    if not queue:
        queue = asyncio.Queue()
        conn.set_extra_info(file_queue=queue)
    return queue


@dataclass
class SFTPFactory(asyncssh.SFTPServer):
    chroot: bool = True
    base_upload_dir: Path = settings.HOME.joinpath('sftp')
    remove_tmp_files: bool = True

    def __init__(self, conn, chroot: bool = True, base_upload_dir: Path = settings.HOME.joinpath('sftp'),
                 remove_tmp_files=True):
        self._scheduler = TaskScheduler()
        conn.set_extra_info(sftp_factory=self)
        self._adaptor = conn.get_extra_info('adaptor')
        if chroot:
            root = base_upload_dir.joinpath(conn.get_extra_info('username'))
            root.mkdir(parents=True, exist_ok=True)
            super().__init__(conn, chroot=root)
        else:
            super().__init__(conn)
        self._remove_tmp_files = remove_tmp_files

    async def _handle_data(self, name: str, data: AnyStr):
        file_stat = await aiofiles.os.stat(name)
        timestamp = datetime.datetime.fromtimestamp(file_stat.st_ctime)
        self._adaptor.on_data_received(data, timestamp=timestamp)
        if self._remove_tmp_files:
            await aremove(name)

    async def _process_completed_file(self, name: str, mode: str):
        mode = 'rb' if mode == 'wb' else 'r'
        async with aiofiles.open(name, mode=mode) as f:
            data = await f.read()
        await self._handle_data(name, data)

    def close(self, file_obj):
        super().close(file_obj)
        self._scheduler.task_with_callback(self._process_completed_file(file_obj.name, file_obj.mode))

    async def wait_closed(self):
        await self._scheduler.close()


@dataclass
class SSHServer(NetworkConnectionProtocol, asyncssh.SSHServer):
    conn = None

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        self.conn = conn
        extra_context = {
            'username': conn.get_extra_info('username'),
            'client_version': conn.get_extra_info('client_version'),
            'server_version': conn.get_extra_info('server_version'),
            'send_cipher': conn.get_extra_info('send_cipher'),
            'send_mac': conn.get_extra_info('send_mac'),
            'send_compression': conn.get_extra_info('send_compression'),
            'recv_cipher': conn.get_extra_info('recv_cipher'),
            'recv_mac': conn.get_extra_info('recv_mac'),
            'recv_compression': conn.get_extra_info('recv_compression'),
        }
        self.initialize_connection(conn, **extra_context)
        self.conn.set_extra_info(adaptor=self._adaptor)

    async def _close(self, exc: Optional[BaseException]) -> None:
        try:
            sftp_factory = self.conn.get_extra_info('sftp_factory')
            await sftp_factory.wait_closed()
        finally:
            await super().close()

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.finish_connection(exc)

    def send(self, msg):
        raise ServerException('Unable to send messages with this receiver')


@dataclass
class SSHServerPublicKeyAuth(SSHServer):
    def public_key_auth_supported(self):
        return True


@dataclass
class BaseSSHServerPswAuth(SSHServer):

    def get_password(self, username: str) -> str:
        raise NotImplementedError

    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return True

    def check_user_password(self, username: str, password: str) -> bool:
        raise NotImplementedError

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.info('Beginning password authentication for user %s', username)
        authorized = self.check_user_password(username, password)
        if authorized:
            self.logger.info('SFTP User % successfully authorized', username)
        else:
            self.logger.error('SFTP Login with user %s failed', username)
        return authorized


class SSHServerPswAuthLogins(BaseSSHServerPswAuth):
    hash_algorithm = pbkdf2_sha256

    def __init__(self, *args, logins: Dict[str, str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.logins = logins

    def hash_password(self, password: str) -> str:
        return self.hash_algorithm.hash(password)

    def check_user_password(self, username: str, password: str) -> bool:
        pw_hash = self.get_password(username)
        if not pw_hash:
            self.logger.error('Could not find user %s', username)
        return self.hash_algorithm.verify(password, pw_hash)

    def get_password(self, username: str) -> Union[str, bool]:
        return self.logins.get(username)

    def password_auth_supported(self) -> bool:
        return bool(self.logins)


@dataclass
class SFTPServer(BaseNetworkServer):
    protocol_factory = SSHServer
    sftp_factory = SFTPFactory
    name = 'SFTP Server'
    peer_prefix = 'tcp'
    sftploglevel: InitVar[int] = 1
    allow_scp: bool = False
    server_host_key: Path = ()
    passphrase: str = None
    authorized_keys: Path = None
    extra_sftp_kwargs: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self, sftploglevel) -> None:
        asyncssh.logging.set_debug_level(sftploglevel)

    @property
    def sftp_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            'allow_scp': self.allow_scp,
            'server_host_keys': self.server_host_key,
            'passphrase': self.passphrase,
            'authorized_client_keys': str(self.authorized_keys) if self.authorized_keys else None
        }
        kwargs.update(self.extra_sftp_kwargs)
        return kwargs

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        return {'public_key_auth_supported': bool(self.authorized_keys)}

    async def get_server(self):
        server_factory = partial(self.protocol_factory, **self.connection_kwargs)
        return await asyncssh.create_server(server_factory, self.host, self.port, sftp_factory=self.sftp_factory,
                                            **self.sftp_kwargs)


@dataclass
class SFTPServerPswAuth(SFTPServer):
    protocol_factory = SSHServerPswAuthLogins
    logins: Dict[str, str] = field(default_factory=dict)

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        kwargs = super().connection_kwargs
        kwargs['logins'] = self.logins
        return kwargs


