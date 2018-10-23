import asyncssh
import os
import logging
from passlib.hash import pbkdf2_sha256
from .asyncio_servers import ServerProtocolMixin
from .base import BaseServer

logger = logging.getLogger('messageManager')


class SFTPFactory(ServerProtocolMixin, asyncssh.SFTPServer):

    def __init__(self, receiver, conn):
        root = receiver.base_upload_dir + conn.get_extra_info('username')
        os.makedirs(root, exist_ok=True)
        super().__init__(conn, chroot=root)
        self.logger = logger
        self.receiver = receiver

    def close(self, file_obj):
        super(SFTPFactory, self).close(file_obj)
        print('File upload complete')
        # self.on_data_received('username', data)


class SFTPFactoryPswAuth(SFTPFactory):
    hash_algorithm = pbkdf2_sha256

    def get_password(self, username):
        return self.receiver.logins.get(username)

    def begin_auth(self, username):
        return self.get_password(username) != ''

    @staticmethod
    def password_auth_supported():
        return True

    def hash_password(self, password):
        return self.hash_algorithm.hash(password)

    def validate_password(self, username, password):
        pw_hash = self.get_password(username)
        return self.hash_algorithm.verify(password, pw_hash)


class SFTPServer(BaseServer):
    factory = SFTPFactory
    receiver_type = 'SFTP Server'

    def __init__(self, manager, config, **kwargs):
        super(BaseServer, self).__init__(manager, config, **kwargs)
        self.allow_scp = self.config.get('allow_scp', False)
        self.base_upload_dir = self.config.get('base_upload_dir')

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def start_server(self):
        self.server = await asyncssh.listen(self.host, self.port,
                                            sftp_factory=lambda conn: self.factory(self, conn),
                                            allow_scp=self.allow_scp)
        async with self.server:
            self.set_status_changed('started')
            await self.server.serve_forever()


class SFTPServerPswAuth(SFTPServer):
    factory = SFTPFactoryPswAuth

    def __init__(self, manager, config, **kwargs):
        self.logins = config.logins
        super(SFTPServerPswAuth, self).__init__(manager, config, **kwargs)
