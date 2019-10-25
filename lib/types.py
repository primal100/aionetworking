from collections import ChainMap
from pathlib import Path
import builtins
from functools import partial
import operator
import yaml

from ipaddress import IPv4Network, IPv6Network, AddressValueError

from typing import Union, Callable, Iterable, Any, Sequence, Optional


from dataclasses import dataclass


"""class Logger(logging.Logger):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[str, logging.Logger]) -> logging.Logger:
        if isinstance(value, str):
            return logging.getLogger(value)
        return value"""


class IPNetwork:
    def __init__(self, network: Union[str, IPv4Network, IPv6Network]):
        if isinstance(network, IPv4Network):
            self.ip_network = network
            self.is_ipv6 = False
        elif isinstance(network, IPv6Network):
            self.ip_network = network
            self.is_ipv6 = True
        else:
            try:
                self.ip_network = IPv4Network(network)
                self.is_ipv6 = False
            except AddressValueError:
                try:
                    self.ip_network = IPv6Network(network)
                    self.is_ipv6 = True
                except AddressValueError:
                    raise AddressValueError(f'{network} is not valid IPv4 or IPv6 network')

    def __eq__(self, other):
        return self.ip_network == other.ip_network

    def supernet_of(self, network: Union[IPv4Network, IPv6Network]):
        return self.ip_network.supernet_of(network)


def supernet_of(network: Union[str, IPNetwork, IPv4Network, IPv6Network], networks: Sequence[IPNetwork]):
    if not isinstance(network, IPNetwork):
        network = IPNetwork(network)
    if network.is_ipv6:
        networks = filter(lambda n: n.is_ipv6, networks)
    else:
        networks = filter(lambda n: not n.is_ipv6, networks)
    return any(n.supernet_of(network.ip_network) for n in networks)


@dataclass
class CallableFromString(Callable):
    _strings_to_callables = {}
    callable: Callable

    def __post_init__(self):
        self.callable = self.adapt_callable(self.callable)

    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)

    def adapt_callable(self, v: Union[str, Callable]):
        if isinstance(v, str):
            try:
                return self._strings_to_callables[v]
            except KeyError:
                raise TypeError(f"{v} not found")
        if v not in self._strings_to_callables.values():
            name = self.__class__.__name__
            raise TypeError(f"{v} not a valid {name}")
        return v


class Builtin(CallableFromString):
    _strings_to_callables = ChainMap(builtins.__dict__, {'istr': str})


def in_(a, b) -> bool:
    return a in b


class Operator(CallableFromString):
    _strings_to_callables = {
        '=': operator.eq,
        '==': operator.eq,
        'eq': operator.eq,
        '<': operator.lt,
        'lt': operator.lt,
        '<=': operator.le,
        'lte': operator.le,
        '!<': operator.ne,
        'ne': operator.ne,
        '>': operator.gt,
        'gt': operator.gt,
        '>=': operator.ge,
        'ge': operator.ge,
        'in': in_,
        'contains': operator.contains
    }


@dataclass
class Expression:
    attr: str
    op: Operator
    value_type: Builtin
    value: Any
    case_sensitive: bool = True

    @classmethod
    def from_string(cls, string: str):
        attr, op, value_type, value = string.split()
        if op.startswith('i'):
            case_sensitive = True
            op = op.split('i')[1]
        else:
            case_sensitive = False
        op = Operator(op)
        return cls(attr, op, value_type, value, case_sensitive=case_sensitive)

    def __call__(self, obj: Any) -> bool:
        if not self.attr or self.attr == 'self':
            value = obj
        else:
            value = getattr(obj, self.attr)
        if self.case_sensitive:
            if isinstance(value, Iterable):
                value = [v.lower() for v in value]
            else:
                value = value.lower()
            return self.op(value, self.value.lower())
        return self.op(value, self.value)


"""
class FilePathNewOK(Path):
    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield path_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: Path) -> Path:
        if not value.exists():
            value.parent.mkdir(exists_ok=True, parents=True)
        if not value.is_file():
            raise errors.PathNotAFileError(path=value)
        return value


class DirectoryPathNewOK(Path):
    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield path_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: Path) -> Path:
        if not value.exists():
            value.parent.mkdir(exists_ok=True, parents=True)
        if not value.is_dir():
            raise errors.PathNotADirectoryError(path=value)
        return value
"""


def path_constructor(loader, node) -> Optional[Path]:
    value = loader.construct_scalar(node)
    if value:
        path = Path(value)
        path.mkdir(exist_ok=True, parents=True)
        return path
    return None


def load_path(Loader=yaml.SafeLoader):
    yaml.add_constructor('!Path', path_constructor, Loader=Loader)


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