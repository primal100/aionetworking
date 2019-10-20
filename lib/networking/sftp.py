from datetime import datetime
from lib.conf.context import context_cv

import asyncssh
import aiofiles.os
import asyncio
from dataclasses import dataclass
from .exceptions import ProtocolException

from lib import settings
from lib.wrappers.schedulers import TaskScheduler
from lib.compatibility import cached_property
from .adaptors import ReceiverAdaptor, SenderAdaptor
from .protocol_factories import BaseProtocolFactory
from .connections import NetworkConnectionProtocol
from lib.utils import aremove

from typing import Optional, AnyStr, Union
from pathlib import Path


@dataclass
class SFTPFactory(asyncssh.SFTPServer):
    chroot = True
    remove_tmp_files = True
    base_upload_dir: Path = settings.TEMPDIR / "sftp_received"

    def __init__(self, conn, base_upload_dir: Path = settings.HOME.joinpath('sftp')):
        self._scheduler = TaskScheduler()
        self._conn = conn
        self._conn.set_extra_info(sftp_factory=self)
        if self.chroot:
            root = base_upload_dir.joinpath(self._conn.get_extra_info('username'))
            root.mkdir(parents=True, exist_ok=True)
            super().__init__(self._conn, chroot=root)
        else:
            super().__init__(self._conn)

    @cached_property
    def sftp_connection(self):
        return self._conn.get_extra_info('sftp_connection')

    async def _handle_data(self, name: str, data: AnyStr):
        file_stat = await aiofiles.os.stat(name)
        timestamp = datetime.fromtimestamp(file_stat.st_ctime)
        self.sftp_connection.data_received(data, timestamp=timestamp)
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
class SFTPServerProtocol(NetworkConnectionProtocol, asyncssh.SSHServer):
    name = 'SFTP Server'
    conn = None
    adaptor_cls = ReceiverAdaptor

    def connection_made(self, conn: Union[asyncssh.SSHServerConnection, asyncssh.SSHClientConnection]) -> None:
        self.conn = conn
        extra_context = {
            'username': conn.get_extra_info('username')
            #'client_version': conn.get_extra_info('client_version'),
            #'server_version': conn.get_extra_info('server_version'),
            #'send_cipher': conn.get_extra_info('send_cipher'),
            #'send_mac': conn.get_extra_info('send_mac'),
            #'send_compression': conn.get_extra_info('send_compression'),
            #'recv_cipher': conn.get_extra_info('recv_cipher'),
            #'recv_mac': conn.get_extra_info('recv_mac'),
            #'recv_compression': conn.get_extra_info('recv_compression'),
        }
        self.initialize_connection(conn, **extra_context)
        self.conn.set_extra_info(sftp_connection=self)

    async def _close(self, exc: Optional[BaseException]) -> None:
        try:
            sftp_factory = self.conn.get_extra_info('sftp_factory')
            await sftp_factory.wait_closed()
        finally:
            await super()._close(exc)

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.finish_connection(exc)

    def send(self, msg):
        raise ProtocolException('Unable to send messages with this receiver')


@dataclass
class BaseSFTPServerPswAuth(SFTPServerProtocol):

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
    connection_cls = SFTPServerProtocol


@dataclass
class SFTPClientProtocol(SFTPServerProtocol):
    name = 'SFTP Client'
    store_connections = False
    adaptor_cls = SenderAdaptor
    sftp = None
    cwd = None
    mode = 'wb'
    remove_tmp_files: bool = True
    prefix: str = 'FILE'
    base_path: Path = settings.TEMPDIR / "sftp_sent"

    def __post_init__(self):
        super().__post_init__()
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def set_sftp(self, sftp):
        self.sftp = sftp
        self.cwd = await self.sftp.realpath('.')

    def get_filename(self):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return self.prefix + timestamp

    def get_tmp_path(self):
        return self.base_path / self.get_filename()

    async def _put_data(self, file_path: Path, data: bytes, **kwargs):
        async with settings.FILE_OPENER(file_path, self.mode) as f:
            await f.write(data)
        remote_path = self.cwd + file_path.name
        real_remote_path = await self.sftp.realpath(remote_path)
        kwargs['remotepath'] = kwargs.get('remotepath', str(real_remote_path))
        await self.sftp.put(str(file_path), **kwargs)
        if self.remove_tmp_files:
            await aremove(file_path)

    def send(self, data: bytes) -> asyncio.Task:
        file_path = self.get_tmp_path()
        self.logger.debug("Using temp path for sending file: %s", file_path)
        task = asyncio.create_task(self._put_data(file_path, data))
        return task


@dataclass
class SFTPClientProtocolFactory(BaseProtocolFactory):
    connection_cls = SFTPClientProtocol
    remove_tmp_files: bool = True
    prefix: str = 'FILE'
    base_path: Path = settings.TEMPDIR / "sftp_sent"

    def _new_connection(self) -> SFTPClientProtocol:
        context_cv.set(context_cv.get().copy())
        self.logger.debug('Creating new connection')
        return self.connection_cls(parent_name=self.full_name, peer_prefix=self.peer_prefix, action=self.action,
                                   preaction=self.preaction, requester=self.requester, dataformat=self.dataformat,
                                   pause_reading_on_buffer_size=self.pause_reading_on_buffer_size, logger=self.logger,
                                   remove_tmp_files = self.remove_tmp_files, prefix=self.prefix, base_path=self.base_path)

