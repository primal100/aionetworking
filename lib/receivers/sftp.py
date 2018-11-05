import asyncssh
import logging
from passlib.hash import pbkdf2_sha256

import settings
from lib.connection_protocols.asyncio_protocols import ServerProtocolMixin
from .base import BaseServer

from typing import Mapping
from pathlib import Path


logger = logging.getLogger(settings.LOGGER_NAME)


class SFTPFactory(ServerProtocolMixin, asyncssh.SFTPServer):

    def __init__(self, receiver, conn):
        #receiver.check_sender
        root = receiver.base_upload_dir.joinpath(conn.get_extra_info('username'))
        root.mkdir(parents=True, exist_ok=True)
        super().__init__(conn, chroot=root)
        self.logger = logger
        self.receiver = receiver

    def close(self, file_obj):
        super(SFTPFactory, self).close(file_obj)
        print('File upload complete')
        # self.on_data_received('username', data)


class SFTPFactoryPswAuth(SFTPFactory):
    hash_algorithm = pbkdf2_sha256

    def get_password(self, username: str) -> str:
        return self.receiver.logins[username]

    def begin_auth(self, username: str) -> bool:
        return self.get_password(username) != ''

    @staticmethod
    def password_auth_supported() -> bool:
        return True

    def hash_password(self, password: str) -> str:
        return self.hash_algorithm.hash(password)

    def validate_password(self, username: str, password: str) -> bool:
        pw_hash = self.get_password(username)
        return self.hash_algorithm.verify(password, pw_hash)


class SFTPServer(BaseServer):
    factory = SFTPFactory
    receiver_type = 'SFTP Server'

    configurable = BaseServer.configurable.copy()
    configurable.update({'allow_scp': bool, 'base_upload_dir': Path})

    def __init__(self, manager, *args, allow_scp: bool=False,
                 base_upload_dir: Path=settings.HOME.joinpath('sftp'), **kwargs):
        super(BaseServer, self).__init__(manager, *args, **kwargs)
        self.allow_scp = allow_scp
        self.base_upload_dir = base_upload_dir

    async def start_server(self):
        self.server = await asyncssh.listen(self.host, self.port,
                                            sftp_factory=lambda conn: self.factory(self, conn),
                                            allow_scp=self.allow_scp)
        async with self.server:
            self.set_status_changed('started')
            await self.server.serve_forever()

    async def stop_server(self):
        if self.server:
            self.server.stop()
            await self.server.wait_closed()


class SFTPServerPswAuth(SFTPServer):
    factory = SFTPFactoryPswAuth

    configurable = SFTPServer.configurable.copy()
    configurable.update({'Logins': dict})

    def __init__(self, manager, logins: Mapping[str, str], *args, **kwargs):
        self.logins = logins
        super(SFTPServerPswAuth, self).__init__(manager, *args, **kwargs)


