from dataclasses import dataclass
from .sftp import SSHServer, SFTPServer
import pamela


@dataclass
class SSHServerPamAuth(SSHServer):

    def validate_password(self, username: str, password: str) -> bool:
        self.logger.debug('Attempting login with PAM')
        try:
            pamela.authenticate(username, password)
            return True
        except pamela.PAMError:
            return False


@dataclass
class SFTPServerPamAuth(SFTPServer):
    protocol_factory = SSHServerPamAuth
