import yaml
from .sftp import SFTPServer


def sftp_server_constructor(loader, node) -> SFTPServer:
    value = loader.construct_mapping(node) if node.value else {}
    return SFTPServer(**value)


def load_sftp_server(Loader=yaml.SafeLoader):
    yaml.add_constructor('!SFTPServer', sftp_server_constructor, Loader=Loader)
