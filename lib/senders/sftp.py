import asyncssh
import os
import binascii
from functools import partial
from pathlib import Path

from .asyncio_clients import BaseAsyncioClient
from lib import settings
from lib.networking.asyncio_protocols import TCPClientProtocol
from lib.conf import RawStr
from .exceptions import ClientException


class SSHClient(TCPClientProtocol, asyncssh.SSHClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def send(self, msg):
        raise ClientException('Cannot send from connection protocol')


class SFTPClient(BaseAsyncioClient):
    protocol_cls = SSHClient
    configurable = BaseAsyncioClient.configurable.copy()
    configurable.update({'basepath': Path, 'filename': RawStr, 'remotepath': Path, 'sftploglevel': int,
                         'knownhosts': Path, 'username': str, 'password': str, 'clientkeys': Path,
                         'passphrase': None, 'clientversion': RawStr, 'removetmpfiles': bool})
    sender_type = 'SFTP Client'
    sftp_client = None
    sftp = None
    conn = None
    cwd = None

    def __init__(self, *args, port=asyncssh.connection._DEFAULT_PORT, srcport=asyncssh.connection._DEFAULT_PORT,
                 basepath=settings.DATA_DIR.joinpath('tmp'), filename=None, remotepath=Path('.'),
                 knownhosts: Path=None, username: str=None, password: str=None, sftp_kwargs=None,
                 clientkeys: Path=(), passphrase: str=None, clientversion:str = (), removetmpfiles = True, **kwargs):
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
        self.remove_tmp_files = removetmpfiles

    async def open_connection(self, **kwargs):
        self.conn, self.sftp_client = await asyncssh.create_connection(
            partial(self.protocol_cls, self.manager, logger=self.logger),
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

    def get_tmp_file_path(self, filename=None):
        if not filename:
            filename = binascii.hexlify(os.urandom(12)).decode('utf-8')
        return self.base_path.joinpath(filename)

    def encode_msg(self, msg_decoded):
        msg_obj = self.manager.protocol.from_decoded(msg_decoded, sender=self.source)
        if self.filename:
            filename = self.filename.format(msg=msg_obj)
        else:
            filename = None
        data = msg_obj.encoded
        return data, filename

    async def encode_and_send_msg(self, msg_decoded):
        data, filename = self.encode_msg(msg_decoded)
        await self.send_msg(data, filename=filename)

    async def send_data(self, data, filename=None):
        file_path = self.get_tmp_file_path(filename)
        self.logger.debug("Using temp path: %s", file_path)
        with file_path.open(self.mode) as f:
            f.write(data)
        await self.put(file_path)
        if self.remove_tmp_files:
            file_path.unlink()

    async def send_msgs(self, msgs):
        await self.send_msgs_sequential(msgs)
