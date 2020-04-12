
import yaml
from .ssl import ServerSideSSL, ClientSideSSL
from .protocol_factories import (StreamServerProtocolFactory, DatagramServerProtocolFactory,
                                 StreamClientProtocolFactory, DatagramClientProtocolFactory)


def ssl_server_side_constructor(loader, node) -> ServerSideSSL:
    value = loader.construct_mapping(node) if node.value else {}
    return ServerSideSSL(**value)


def ssl_client_side_constructor(loader, node) -> ClientSideSSL:
    value = loader.construct_mapping(node) if node.value else {}
    return ClientSideSSL(**value)


def stream_server_protocol_factory_constructor(loader, node) -> StreamServerProtocolFactory:
    value = loader.construct_mapping(node) if node.value else {}
    return StreamServerProtocolFactory(**value)


def datagram_server_protocol_factory_constructor(loader, node) -> DatagramServerProtocolFactory:
    value = loader.construct_mapping(node) if node.value else {}
    return DatagramServerProtocolFactory(**value)


def stream_client_protocol_factory_constructor(loader, node) -> StreamClientProtocolFactory:
    value = loader.construct_mapping(node) if node.value else {}
    return StreamClientProtocolFactory(**value)


def datagram_client_protocol_factory_constructor(loader, node) -> DatagramClientProtocolFactory:
    value = loader.construct_mapping(node) if node.value else {}
    return DatagramClientProtocolFactory(**value)


def load_server_side_ssl(Loader=yaml.SafeLoader):
    yaml.add_constructor('!ServerSideSSL', ssl_server_side_constructor, Loader=Loader)


def load_client_side_ssl(Loader=yaml.SafeLoader):
    yaml.add_constructor('!ClientSideSSL', ssl_client_side_constructor, Loader=Loader)


def load_stream_server_protocol_factory(Loader=yaml.SafeLoader):
    yaml.add_constructor('!StreamServerProtocolFactory', stream_server_protocol_factory_constructor, Loader=Loader)


def load_datagram_server_protocol_factory(Loader=yaml.SafeLoader):
    yaml.add_constructor('!DatagramServerProtocolFactory', datagram_server_protocol_factory_constructor, Loader=Loader)


def load_stream_client_protocol_factory(Loader=yaml.SafeLoader):
    yaml.add_constructor('!StreamClientProtocolFactory', stream_client_protocol_factory_constructor, Loader=Loader)


def load_datagram_client_protocol_factory(Loader=yaml.SafeLoader):
    yaml.add_constructor('!DatagramClientProtocolFactory', datagram_client_protocol_factory_constructor, Loader=Loader)
