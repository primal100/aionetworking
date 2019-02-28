import asyncssh
import os
import binascii
from pathlib import Path

from .base import BaseNetworkClient
from lib import settings
from lib.connection_protocols.asyncio_protocols import TCPClientProtocol
from lib.conf import RawStr
from .exceptions import ClientException

from typing import AnyStr


class SSHClient(TCPClientProtocol, asyncssh.SSHClient):

    def send(self, msg):
        raise ClientException('Cannot send from connection protocol')


class SFTPClient(BaseNetworkClient):
    connection_protocol = SSHClient
    configurable = BaseNetworkClient.configurable.copy()
    configurable.update({'basepath': Path, 'filename': RawStr, 'remotepath': Path, 'sftploglevel': int,
                         'knownhosts': Path, 'username': str, 'password': str, 'clientkeys': Path,
                         'passphrase': None, 'clientversion': RawStr})
    sender_type = 'SFTP Client'
    sftp_client = None
    sftp = None
    conn = None
    cwd = None

    def __init__(self, *args, port=asyncssh.connection._DEFAULT_PORT, srcport=asyncssh.connection._DEFAULT_PORT,
                 basepath=settings.DATA_DIR.joinpath('tmp'), filename=None, remotepath=Path('.'),
                 knownhosts: Path=None, username: str=None, password: str=None, sftp_kwargs=None,
                 clientkeys: Path=(), passphrase: str=None, clientversion:str = (), **kwargs):
        self.filename = filename
        self.remotepath = remotepath
        self.base_path = basepath
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.sftp_kwargs = {'known_hosts': str(knownhosts), 'username': username, 'password': password,
                                 'client_keys': clientkeys,
                                 'passphrase': passphrase, 'client_version': clientversion}
        self.sftp_kwargs.update(sftp_kwargs)
        super(SFTPClient, self).__init__(*args, port=port, srcport=srcport, **kwargs)
        self.mode = 'ba' if self.manager.protocol.binary else 'a'

    async def open_connection(self, **kwargs):
        self.conn, self.sftp_client = await asyncssh.create_connection(
            lambda: self.connection_protocol(self.manager, logger_name=self.logger_name),
            self.host, self.port, local_addr=self.localaddr, **self.sftp_kwargs)
        self.sftp = await self.conn.start_sftp_client()
        self.cwd = await self.sftp.realpath('.')

    async def close_connection(self):
        self.sftp.exit()
        self.conn.close()
        await self.conn.wait_closed()

    async def put(self, file_path, **kwargs):
        remote_path = self.cwd + file_path.name
        real_remote_path = await self.sftp.realpath(remote_path)
        kwargs['remotepath'] = kwargs.get('remotepath', str(real_remote_path))
        await self.sftp.put(str(file_path), **kwargs)

    def encode_msg(self, msg_decoded):
        msg_obj = self.manager.protocol.from_decoded(msg_decoded, sender=self.source)
        if self.filename:
            filename = self.filename.format(msg=msg_obj)
        else:
            filename = binascii.hexlify(os.urandom(12)).decode('utf-8')
        path = self.base_path.joinpath(filename)
        self.logger.debug(path)
        data = msg_obj.encoded
        self.raw_log.debug(data)
        with path.open(self.mode) as f:
            f.write(data)
        return path

    async def encode_and_send_msg(self, msg_decoded):
        file_path = self.encode_msg(msg_decoded)
        await self.send_msg(file_path)
        file_path.unlink()

    async def send_data(self, file_path: AnyStr):
        await self.put(file_path)
