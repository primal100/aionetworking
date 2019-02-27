import asyncssh
import os
import binascii
from pathlib import Path

from .base import BaseNetworkClient
from lib import settings
from lib.conf import RawStr

from typing import AnyStr


class SFTPClient(BaseNetworkClient):
    configurable = BaseNetworkClient.configurable.copy()
    configurable.update({'basepath': Path, 'filename': RawStr, 'remotepath': Path, 'sftploglevel': int})
    sender_type = 'SFTP Client'
    sftp = None
    conn = None

    def __init__(self, *args, basepath=settings.DATA_DIR.joinpath('tmp'), filename=None, remotepath=Path('.'),
                 sftp_kwargs=None, **kwargs):
        self.filename = filename
        self.remotepath = remotepath
        self.base_path = basepath
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.sftp_kwargs = sftp_kwargs or {}
        super(SFTPClient, self).__init__(*args, **kwargs)
        self.mode = 'ba' if self.manager.protocol.binary else 'a'

    async def open_connection(self, **kwargs):
        self.conn = await asyncssh.connect(self.host, self.port, **self.sftp_kwargs)
        self.sftp = await self.conn.start_sftp_client()

    async def close_connection(self):
        self.sftp.exit()
        self.conn.close()
        await self.conn.wait_closed()

    async def put(self, *args, **kwargs):
        kwargs['remotepath'] = kwargs.get('remotepath', self.remotepath)
        await self.sftp.put(*args, **kwargs)

    def encode_msg(self, msg_decoded):
        msg_obj = self.manager.protocol.from_decoded(msg_decoded, sender=self.source)
        if self.filename:
            filename = self.filename.format(msg=msg_obj)
        else:
            filename = binascii.hexlify(os.urandom(12)).decode('utf-8')
        path = self.base_path.joinpath(filename)
        self.log.debug(path)
        data = msg_obj.encoded
        self.raw_log.debug(data)
        with path.open(self.mode) as f:
            f.write(data)
        return path

    async def encode_and_send_msg(self, msg_decoded):
        file_path = self.encode_msg(msg_decoded)
        await self.send_msg(file_path)
        file_path.remove()

    async def send_data(self, file_path: AnyStr):
        await self.put(str(file_path))
