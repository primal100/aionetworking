import yaml
from .base import EmptyAction
from .echo import EchoAction
from .file_storage import FileStorage, BufferedFileStorage


def echo_action_constructor(loader, node) -> EchoAction:
    value = loader.construct_mapping(node) if node.value else {}
    return EchoAction(**value)


def empty_action_constructor(loader, node) -> EmptyAction:
    value = loader.construct_mapping(node) if node.value else {}
    return EmptyAction(**value)


def file_storage_constructor(loader, node) -> FileStorage:
    value = loader.construct_mapping(node) if node.value else {}
    return FileStorage(**value)


def buffered_file_storage_constructor(loader, node) -> BufferedFileStorage:
    value = loader.construct_mapping(node) if node.value else {}
    return BufferedFileStorage(**value)


def load_echo_action(Loader=yaml.SafeLoader):
    yaml.add_constructor('!EchoAction', echo_action_constructor, Loader=Loader)


def load_empty_action(Loader=yaml.SafeLoader):
    yaml.add_constructor('!EmptyAction', empty_action_constructor, Loader=Loader)


def load_file_storage(Loader=yaml.SafeLoader):
    yaml.add_constructor('!FileStorage', file_storage_constructor, Loader=Loader)


def load_buffered_file_storage(Loader=yaml.SafeLoader):
    yaml.add_constructor('!BufferedFileStorage', buffered_file_storage_constructor, Loader=Loader)

