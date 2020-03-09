import asyncssh
import asyncio
from dataclasses import dataclass, field, InitVar
from functools import partial

from aionetworking import settings
from aionetworking.networking.sftp import SFTPServerProtocolFactory, SFTPFactory
from .base import BaseNetworkServer

from typing import Dict, Any, Union
from pathlib import Path


@dataclass
class SFTPServer(BaseNetworkServer):
    protocol_factory: SFTPServerProtocolFactory = None
    sftp_factory = SFTPFactory
    name = 'SFTP Server'
    peer_prefix = 'sftp'
    reuse_address: bool = True
    sftp_log_level: InitVar[int] = 1
    allow_scp: bool = False
    server_host_key: Path = ()
    passphrase: str = None
    extra_sftp_kwargs: Dict[str, Any] = field(default_factory=dict)
    base_upload_dir: Path = settings.TEMPDIR / "sftp_received"

    def __post_init__(self, sftp_log_level) -> None:
        super().__post_init__()
        asyncssh.logging.set_debug_level(sftp_log_level)

    @property
    def sftp_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            'allow_scp': self.allow_scp,
            'server_host_keys': [self.server_host_key],
            'passphrase': self.passphrase,
        }
        kwargs.update(self.extra_sftp_kwargs)
        return kwargs

    async def _get_server(self) -> asyncio.AbstractServer:
        return await asyncssh.create_server(self.protocol_factory, self.host, self.port, backlog=self.backlog,
                                            reuse_address=self.reuse_address, reuse_port=self.reuse_port, line_editor=False,
                                            sftp_factory=partial(self.sftp_factory, base_upload_dir=self.base_upload_dir),
                                            **self.sftp_kwargs)


def generate_key_in_path(path: Union[Path, str], alg_name='ssh-rsa'):
    skey = asyncssh.generate_private_key(alg_name)
    skey.write_private_key(str(path))
