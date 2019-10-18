import asyncssh
import aiofiles.os
import asyncio
import datetime
from dataclasses import dataclass, field, InitVar
from functools import partial

from lib import settings
from lib.wrappers.schedulers import TaskScheduler
from lib.networking.protocol_factories import BaseProtocolFactory
from lib.networking.connections import NetworkConnectionProtocol
from lib.utils import aremove
from .base import BaseNetworkServer
from .exceptions import ServerException

from typing import Dict, Any, Optional, AnyStr
from pathlib import Path


@dataclass
class SFTPFactory(asyncssh.SFTPServer):
    chroot = True
    remove_tmp_files = True
    base_upload_dir: Path = settings.TEMPDIR / "sftp_received"

    def __init__(self, conn, base_upload_dir: Path = settings.HOME.joinpath('sftp')):
        self._scheduler = TaskScheduler()
        conn.set_extra_info(sftp_factory=self)
        self._sftp_connection = conn.get_extra_info('adaptor')
        if self.chroot:
            root = base_upload_dir.joinpath(conn.get_extra_info('username'))
            root.mkdir(parents=True, exist_ok=True)
            super().__init__(conn, chroot=root)
        else:
            super().__init__(conn)

    async def _handle_data(self, name: str, data: AnyStr):
        file_stat = await aiofiles.os.stat(name)
        timestamp = datetime.datetime.fromtimestamp(file_stat.st_ctime)
        self._sftp_connection.data_received(data, timestamp=timestamp)
        if self.remove_tmp_files:
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
        self.conn.set_extra_info(sftp_connection=self)

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


@dataclass
class SFTPServerProtocolFactory(BaseProtocolFactory):
    full_name = 'SFTP Server'
    peer_prefix = 'sftp'
    connection_cls = SSHServer


@dataclass
class SFTPServer(BaseNetworkServer):
    protocol_factory = SFTPServerProtocolFactory
    sftp_factory = SFTPFactory
    name = 'SFTP Server'
    peer_prefix = 'sftp'
    sftp_log_level: InitVar[int] = 1
    allow_scp: bool = False
    server_host_key: Path = ()
    passphrase: str = None
    extra_sftp_kwargs: Dict[str, Any] = field(default_factory=dict)
    base_upload_dir: Path = settings.TEMPDIR / "sftp_received"

    def __post_init__(self, sftp_log_level) -> None:
        asyncssh.logging.set_debug_level(sftp_log_level)

    @property
    def sftp_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            'allow_scp': self.allow_scp,
            'server_host_keys': self.server_host_key,
            'passphrase': self.passphrase,
        }
        kwargs.update(self.extra_sftp_kwargs)
        return kwargs

    async def _get_server(self) -> asyncio.AbstractServer:
        return await asyncssh.create_server(self.protocol_factory, self.host, self.port,
                                            sftp_factory=partial(self.sftp_factory, self.base_upload_dir),
                                            **self.sftp_kwargs)



