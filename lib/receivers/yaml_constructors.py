from __future__ import annotations
from .servers import TCPServer, UDPServer, pipe_server
import yaml


def tcp_server_constructor(loader, node) -> TCPServer:
    value = loader.construct_mapping(node) if node.value else {}
    return TCPServer(**value)


def load_tcp_server(Loader=yaml.SafeLoader):
    yaml.add_constructor('!TCPServer', tcp_server_constructor, Loader=Loader)


def udp_server_constructor(loader, node) -> UDPServer:
    value = loader.construct_mapping(node) if node.value else {}
    return UDPServer(**value)


def load_udp_server(Loader=yaml.SafeLoader):
    yaml.add_constructor('!UDPServer', udp_server_constructor, Loader=Loader)


def pipe_server_constructor(loader, node) -> pipe_server:
    value = loader.construct_mapping(node) if node.value else {}
    return pipe_server(**value)


def load_pipe_server(Loader=yaml.SafeLoader):
    yaml.add_constructor('!PipeServer', pipe_server_constructor, Loader=Loader)
