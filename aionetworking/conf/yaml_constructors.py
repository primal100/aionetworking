from __future__ import annotations
import yaml
import asyncio
import os
from pathlib import Path

from functools import partial
from aionetworking.compatibility import default_server_port, default_client_port
from aionetworking.utils import IPNetwork
from aionetworking.logging import Logger

from typing import Optional, Dict, Union, Sequence


def port_constructor(default_port, loader, node) -> int:
    if node.value:
        value = loader.construct_yaml_int(node)
        if value:
            return value
    return default_port


def load_default_ports():
    yaml.add_constructor('!Port', partial(port_constructor, default_server_port()), Loader=yaml.SafeLoader)
    yaml.add_constructor('!ClientPort', partial(port_constructor, default_client_port()), Loader=yaml.SafeLoader)


def path_constructor(paths, loader, node) -> Optional[Path]:
    value = loader.construct_scalar(node)
    if value:
        path = Path(value.format(**paths))
        return path
    return None


def load_path(paths: Dict[str, Union[str, Path]], Loader=yaml.SafeLoader):
    yaml.add_constructor('!Path', partial(path_constructor, paths), Loader=Loader)


def base_path_constructor(base_path: Path, loader, node) -> Path:
    value = loader.construct_scalar(node)
    return Path(base_path / value)


def load_base_path(tag_name: str, base_path: Path, Loader=yaml.SafeLoader):
    yaml.add_constructor(tag_name, partial(base_path_constructor, base_path), Loader=Loader)


def ip_network_constructor(loader, node) -> Sequence[IPNetwork]:
    values = loader.construct_sequence(node)
    return [IPNetwork(v) for v in values]


def load_ip_network(Loader=yaml.SafeLoader):
    yaml.add_constructor('!IPNetwork', ip_network_constructor, Loader=Loader)


def logger_constructor(loader, node) -> Logger:
    value = loader.construct_mapping(node) if node.value else {}
    return Logger(**value)


def load_logger(Loader=yaml.SafeLoader):
    yaml.add_constructor('!Logger', logger_constructor, Loader=Loader)


def receiver_logger_constructor(loader, node) -> Logger:
    value = loader.construct_mapping(node) if node.value else {}
    return Logger('receiver', **value)


def load_receiver_logger(Loader=yaml.SafeLoader):
    yaml.add_constructor('!ReceiverLogger', receiver_logger_constructor, Loader=Loader)


def sender_logger_constructor(loader, node) -> Logger:
    value = loader.construct_mapping(node) if node.value else {}
    return Logger('sender', **value)


def load_sender_logger(Loader=yaml.SafeLoader):
    yaml.add_constructor('!SenderLogger', sender_logger_constructor, Loader=Loader)