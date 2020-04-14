
import yaml
from .sftp import SFTPClientProtocolFactory
from .sftp_os_auth import SFTPOSAuthProtocolFactory


def sftp_server_protocol_factory_constructor(loader, node) -> SFTPOSAuthProtocolFactory:
    value = loader.construct_mapping(node)
    return SFTPOSAuthProtocolFactory(**value)


def sftp_client_protocol_factory_constructor(loader, node) -> SFTPClientProtocolFactory:
    value = loader.construct_mapping(node)
    return SFTPClientProtocolFactory(**value)


def load_sftp_server_protocol_factory(Loader=yaml.SafeLoader):
    yaml.add_constructor('!SFTPServerProtocolFactory', sftp_server_protocol_factory_constructor, Loader=Loader)


def load_sftp_client_protocol_factory(Loader=yaml.SafeLoader):
    yaml.add_constructor('!SFTPClientProtocolFactory', sftp_client_protocol_factory_constructor, Loader=Loader)