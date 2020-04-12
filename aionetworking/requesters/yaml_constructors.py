
import yaml
from .echo import EchoRequester


def echo_requester_constructor(loader, node) -> EchoRequester:
    value = loader.construct_mapping(node) if node.value else {}
    return EchoRequester(**value)


def load_echo_requester(Loader=yaml.SafeLoader):
    yaml.add_constructor('!EchoRequester', echo_requester_constructor, Loader=Loader)
