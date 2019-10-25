import datetime
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

    def __init__(self, conn, base_upload_dir: Path = settings.APP_HOME.joinpath('sftp')):
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
        self.sftp_connection.data_received(data)
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


class SFTPItem:
    def __init__(self, conn, name):
        self._conn = conn
        self._name = name
        self._value = None

    def __bool__(self):
        if not self._value:
            str(self)
        return bool(self._value)

    def __eq__(self, other):
        return str(self) == str(other)

    def __str__(self):
        if self._value:
            return self._value
        value = self._conn.get_extra_info(self._name)
        if value:
            self._value = str(value)
        return str(value)

    def __repr__(self):
        return str(self._value)


@dataclass
class BaseSFTPProtocol(NetworkConnectionProtocol):
    name = 'SFTP Server'
    conn = None
    adaptor_cls = ReceiverAdaptor
    _log_task = None

    def connection_made(self, conn: Union[asyncssh.SSHServerConnection, asyncssh.SSHClientConnection]) -> None:
        self.conn = conn
        extra_context = {
            'username': SFTPItem(self.conn, 'username'),
            'client_version': SFTPItem(self.conn, 'client_version'),
            'server_version': SFTPItem(self.conn, 'server_version'),
            'send_cipher': SFTPItem(self.conn, 'send_cipher'),
            'send_mac': SFTPItem(self.conn, 'send_mac'),
            'send_compression': SFTPItem(self.conn, 'send_compression'),
            'recv_cipher': SFTPItem(self.conn, 'recv_cipher'),
            'recv_mac': SFTPItem(self.conn, 'recv_mac'),
            'recv_compression': SFTPItem(self.conn, 'recv_compression'),
        }
        self.initialize_connection(conn, **extra_context)
        self.conn.set_extra_info(sftp_connection=self)

    async def wait_context_set(self) -> None:
        while not self.context['send_cipher'] or not self.context['username']:
            await asyncio.sleep(0.000001)

    def _log_context(self, task: asyncio.Task):
        super().log_context()
        self._log_task = None

    def log_context(self):
        self._log_task = asyncio.create_task(self.wait_context_set())
        self._log_task.add_done_callback(self._log_context)

    async def _close(self, exc: Optional[BaseException]) -> None:
        if self._log_task:
            self._log_task.cancel()
        try:
            sftp_factory = self.conn.get_extra_info('sftp_factory')
            if sftp_factory:
                await sftp_factory.wait_closed()
        finally:
            await super()._close(exc)

    def close(self, immediate: bool = False):
        if not self.is_closing():
            self.conn.close()

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self.run_connection_lost_tasks()
        self.finish_connection(exc)

    def send(self, msg):
        raise ProtocolException('Unable to send messages with this receiver')


@dataclass
class SFTPServerProtocol(BaseSFTPProtocol, asyncssh.SSHServer):
    pass


@dataclass
class SFTPServerProtocolFactory(BaseProtocolFactory):
    full_name = 'SFTP Server'
    peer_prefix = 'sftp'
    connection_cls = SFTPServerProtocol


@dataclass
class SFTPClientProtocol(BaseSFTPProtocol, asyncssh.SSHClient):
    name = 'SFTP Client'
    store_connections = False
    adaptor_cls = SenderAdaptor
    sftp = None
    cwd = None
    mode = 'wb'
    strftime: str = "%Y%m%d%H%M%S%f"
    remove_tmp_files: bool = True
    prefix: str = 'FILE'
    base_path: Path = settings.TEMPDIR / "sftp_sent"
    remote_path: str = '/'

    def __post_init__(self):
        super().__post_init__()
        self._name_lock = asyncio.Lock()
        self._last_file_name = None
        self._scheduler = TaskScheduler()
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def set_sftp(self, sftp):
        self.sftp = sftp
        self.remote_path = await self.sftp.realpath(self.remote_path)

    def get_filename(self):
        timestamp = datetime.datetime.now().strftime(self.strftime)
        return self.prefix + timestamp

    async def get_tmp_path(self):
        async with self._name_lock:
            name = None
            while not name or name == self._last_file_name:
                name = self.base_path / self.get_filename()
                await asyncio.sleep(0.000001)
            self._last_file_name = name
            return name

    async def _put_data(self, data: bytes):
        file_path = await self.get_tmp_path()
        self.logger.debug("Using temp path for sending file: %s", file_path)
        async with settings.FILE_OPENER(file_path, self.mode) as f:
            await f.write(data)
        await self.sftp.put(file_path, remotepath=self.remote_path)
        if self.remove_tmp_files:
            await aremove(file_path)

    def send(self, data: bytes) -> asyncio.Future:
        task = self._scheduler.task_with_callback(self._put_data(data))
        return task

    async def wait_tasks_done(self) -> None:
        await self._scheduler.close()

    async def wait_closed(self) -> None:
        await self.wait_tasks_done()
        await super().wait_closed()


@dataclass
class SFTPClientProtocolFactory(BaseProtocolFactory):
    connection_cls = SFTPClientProtocol
    remove_tmp_files: bool = True
    prefix: str = 'FILE'
    base_path: Path = settings.TEMPDIR / "sftp_sent"
    remote_path: str = '/'

    def _new_connection(self) -> SFTPClientProtocol:
        context_cv.set(context_cv.get().copy())
        self.logger.debug('Creating new connection')
        return self.connection_cls(parent_name=self.full_name, peer_prefix=self.peer_prefix, action=self.action,
                                   preaction=self.preaction, requester=self.requester, dataformat=self.dataformat,
                                   pause_reading_on_buffer_size=self.pause_reading_on_buffer_size, logger=self.logger,
                                   remove_tmp_files = self.remove_tmp_files, prefix=self.prefix, base_path=self.base_path,
                                   remote_path=self.remote_path, allowed_senders=self.allowed_senders, aliases=self.aliases)

