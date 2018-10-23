import asyncssh
import logging
from .base import BaseNetworkClient

logger = logging.getLogger('messageManager')


class SFTPClient(BaseNetworkClient):
    sender_type = 'SFTP Client'
    protocol = None
    sftp = None

    @classmethod
    def from_config(cls, receiver_config, client_config, protocols, protocol_name, **kwargs):
        msg_protocol = protocols[protocol_name]
        return cls(msg_protocol, receiver_config['host'], receiver_config['port'],
                   client_config['src_ip'], client_config['src_port'])

    def __init__(self, *args, **kwargs):
        self.sftp_kwargs = kwargs
        super(SFTPClient, self).__init__(*args,)

    async def open_connection(self, **kwargs):
        self.transport, self.protocol = asyncssh.connect(self.host, self.port, **self.sftp_kwargs)
        self.sftp = self.transport.start_sftp_client()

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data):
        filename = 'test'
        with open(filename, 'w') as f:
            f.write(encoded_data)
        await self.sftp.put(filename)
