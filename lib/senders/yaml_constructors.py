import yaml
from .clients import TCPClient, UDPClient, pipe_client


def tcp_client_constructor(loader, node) -> TCPClient:
    value = loader.construct_mapping(node) if node.value else {}
    return TCPClient(**value)


def load_tcp_client(Loader=yaml.SafeLoader):
    yaml.add_constructor('!TCPClient', tcp_client_constructor, Loader=Loader)


def udp_client_constructor(loader, node) -> UDPClient:
    value = loader.construct_mapping(node) if node.value else {}
    return UDPClient(**value)


def load_udp_client(Loader=yaml.SafeLoader):
    yaml.add_constructor('!UDPClient', udp_client_constructor, Loader=Loader)


def pipe_client_constructor(loader, node):
    value = loader.construct_mapping(node) if node.value else {}
    return pipe_client(**value)


def load_pipe_client(Loader=yaml.SafeLoader):
    yaml.add_constructor('!PipeClient', pipe_client_constructor, Loader=Loader)

