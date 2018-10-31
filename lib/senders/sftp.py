import asyncssh
import logging

import settings
from .base import BaseNetworkClient

from typing import AnyStr

logger = logging.getLogger(settings.LOGGER_NAME)


class SFTPClient(BaseNetworkClient):
    sender_type = 'SFTP Client'
    sftp = None
    connection_protocol = None
    transport = None

    def __init__(self, *args, **kwargs):
        self.sftp_kwargs = kwargs
        super(SFTPClient, self).__init__(*args,)

    async def open_connection(self, **kwargs):
        self.transport, self.connection_protocol = asyncssh.connect(self.host, self.port, **self.sftp_kwargs)
        self.sftp = self.transport.start_sftp_client()

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data: AnyStr):
        filename = 'test'
        with open(filename, 'w') as f:
            f.write(encoded_data)
        await self.sftp.put(filename)
