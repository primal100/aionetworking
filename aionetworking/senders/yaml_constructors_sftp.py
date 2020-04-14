
import yaml
from .sftp import SFTPClient


def sftp_client_constructor(loader, node) -> SFTPClient:
    value = loader.construct_mapping(node) if node.value else {}
    return SFTPClient(**value)


def load_sftp_client(Loader=yaml.SafeLoader):
    yaml.add_constructor('!SFTPClient', sftp_client_constructor, Loader=Loader)
