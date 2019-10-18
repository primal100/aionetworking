import asyncssh
import asyncio
from dataclasses import dataclass, InitVar, field
from datetime import datetime
from pathlib import Path

from .clients import BaseNetworkClient
from lib import settings
from lib.conf.context import context_cv
from lib.networking.protocol_factories import BaseProtocolFactory
from lib.networking.connections import NetworkConnectionProtocol


@dataclass
class SSHClientConnection(NetworkConnectionProtocol, asyncssh.SSHClient):
    sftp = None
    cwd = None
    mode = 'wb'
    remove_tmp_files: bool = True
    prefix: str = 'FILE'
    base_path: Path = settings.TEMPDIR / "sftp_sent"

    def __post_init__(self):
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

    def send(self, data: bytes) -> asyncio.Task:
        file_path = self.get_tmp_path()
        self.logger.debug("Using temp path for sending file: %s", file_path)
        task = asyncio.create_task(self._put_data(file_path, data))
        if self.remove_tmp_files:
            file_path.unlink()
        return task


@dataclass
class SSHClientProtocolFactory(BaseProtocolFactory):
    connection_cls = SSHClientConnection
    remove_tmp_files: bool = True
    prefix: str = 'FILE'
    base_path: Path = settings.TEMPDIR / "sftp_sent"

    def _new_connection(self) -> SSHClientConnection:
        context_cv.set(context_cv.get().copy())
        self.logger.debug('Creating new connection')
        return self.connection_cls(parent_name=self.full_name, peer_prefix=self.peer_prefix, action=self.action,
                                   preaction=self.preaction, requester=self.requester, dataformat=self.dataformat,
                                   pause_reading_on_buffer_size=self.pause_reading_on_buffer_size, logger=self.logger,
                                   remove_tmp_files = self.remove_tmp_files, prefix=self.prefix, base_path=self.base_path)


@dataclass
class SFTPClient(BaseNetworkClient):
    name = "SFTP Client"
    protocol_factory = SSHClientProtocolFactory
    sftp_log_level: InitVar[int] = 1
    known_hosts: Path = None
    username: str = None
    password: str = None
    client_keys: Path = None
    passphrase: str = None
    client_version: str = None
    sftp_client = None
    sftp = None
    cwd = None

    def __post_init__(self, sftp_log_level) -> None:
        asyncssh.logging.set_debug_level(sftp_log_level)

    async def _open_connection(self) -> SSHClientConnection:
        self.conn, self.sftp_client = await asyncssh.create_connection(
            self.protocol_factory, self.host, self.port, local_addr=self.src, known_hosts=self.known_hosts,
            username=self.username, password=self.password, client_keys=self.client_keys, passphrase=self.passphrase,
            client_version = self.client_version)
        self.sftp = await self.conn.start_sftp_client()
        await self.conn.set_sftp(self.sftp)
        return self.conn

    async def _close_connection(self) -> None:
        self.sftp.exit()
        self.conn.close()
        await self.conn.wait_closed()
