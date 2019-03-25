from collections import UserList
from functools import partial
import operator
import logging
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from ipaddress import IPv4Network, IPv6Network, AddressValueError

from .logging import Logger
from .base import BaseConfig

from typing import Iterable, MutableMapping, Callable, Type, Union, Any, NoReturn, Tuple, Optional, Generator
from ipaddress import IPv4Address, IPv6Address


class RawStr(str):
    pass


@dataclass
class _BaseConfigurableType:
    config_section = ''
    name = ''
    default_logger_name = ''

    #Dataclass Fields
    logger: Logger = None

    def __post_init__(self):
        pass

    @classmethod
    def get_configurable(cls) -> Iterable:
        return filter(lambda f: f.metadata.get('configurable', True), fields(cls))

    @classmethod
    def get_config_section(cls, section_postfix):
        if section_postfix:
            return f"{cls.config_section}_{section_postfix}"
        return cls.config_section

    @classmethod
    def get_config(cls, section_postfix='', cp: BaseConfig = None, logger: Logger = None, **kwargs) -> MutableMapping:
        from lib import settings
        cp = cp or settings.CONFIG
        section = cls.get_config_section(section_postfix)
        config = cp.section_as_dict(section, cls.get_configurable())
        logger.info('Found configuration for %s: %s', cls.name,  config)
        config.update(kwargs)
        if logger:
            config['logger'] = logger
        else:
            config['logger'] = Logger(cls.default_logger_name)
        return config

    @classmethod
    def with_config(cls, *args, **kwargs) -> Callable:
        config = cls.get_config(**kwargs)
        return partial(cls, *args, **config)

    @classmethod
    def from_config(cls, *args, **kwargs):
        config = cls.get_config(*args, **kwargs)
        return cls(**config)


class BaseConfigurable(_BaseConfigurableType):
    @classmethod
    def from_config(cls, *args, **kwargs) -> _BaseConfigurableType:
        return super().from_config(*args, **kwargs)


class BaseSwappable(BaseConfigurable):

    @classmethod
    def get_swappable(cls, name) -> Type[BaseConfigurable]:
        return BaseConfigurable

    @classmethod
    def swap_from_config(cls, name, *args, **kwargs) -> _BaseConfigurableType:
        klass = cls.get_swappable(name)
        return klass.from_config(*args, **kwargs)


class IPNetwork:
    def __new__(cls, val: Union[str, IPv4Network, IPv6Network]) -> Union[IPv4Network, IPv6Network]:
        try:
            return IPv4Network(val)
        except AddressValueError:
            return IPv6Network(val)


class BaseListCoerce(UserList):
    data_type = str
    data = []

    def __init__(self, values: Union[Iterable, str]):
        if isinstance(values, str):
            if str:
                values = values.replace(', ', ',').split(',')
            else:
                values = []
        values = [self.pre_process(val) for val in values]
        super().__init__(values)

    def pre_process(self, obj, for_insert: bool = True) -> Any:
        return self.data_type(obj)

    def __getattr__(self, item: Any) -> Iterable[Any]:
        return [getattr(i, item) for i in self.data]

    def __setitem__(self, key: int, value) -> NoReturn:
        self.data[key] = self.pre_process(value)

    def __add__(self, other: Any) -> Iterable:
        other_list = self.__class__(other)
        return self.data.__add__(other_list)

    def __contains__(self, item: Any) -> bool:
        return self.pre_process(item) in self.data

    def extend(self, other: Any) -> NoReturn:
        other_list = self.__class__(other)
        self.data.extend(other_list)

    def index(self, item: Any, *args) -> int:
        return self.data.index(self.pre_process(item), *args)

    def insert(self, i: int, item: Any) -> NoReturn:
        self.data.insert(i, self.pre_process(item))

    def append(self, obj: Any) -> NoReturn:
        self.data.append(self.pre_process(obj))

    def remove(self, obj: Any) -> NoReturn:
        self.data.remove(self.pre_process(object))


class Operator:
    def __new__(cls, op) -> Callable:
        return getattr(operator, op)


class DataType:
    def __new__(cls, value):
        try:
            return getattr(__builtins__, value)
        except AttributeError:
            return getattr(sys.modules[__name__], value)


class ListStrings(BaseListCoerce):
    data_type = str


class ListLoggers(BaseListCoerce):
    data_type = logging.getLogger


class BaseListNum(BaseListCoerce):

    @property
    def sum(self) -> Union[int, float]:
        return sum(i for i in self.data)

    @property
    def highest(self) -> Union[int, float]:
        return max(i for i in self.data)

    @property
    def lowest(self) -> Union[int, float]:
        return min(i for i in self.data)

    @property
    def range(self) -> Tuple[Union[int, float], Union[int, float]]:
        return self.lowest, self.highest


class ListFloats(BaseListNum):
    data_type = float


class ListInts(BaseListNum):
    data_type = int


class ListPaths(BaseListCoerce):
    data_type = Path


class ListIPNetworks(BaseListCoerce):
    data_type = IPNetwork

    @property
    def version(self) -> Optional[Union[str, int]]:
        ip4 = any(n.version == '4' for n in self.data)
        ip6 = any(n.version == '6' for n in self.data)
        if ip4 and ip6:
            return 'mixed'
        elif ip4:
            return '4'
        elif ip6:
            return '6'
        else:
            return None

    @property
    def num_addresses(self) -> int:
        return sum(n.num_addresses for n in self.data)

    def hosts(self) -> Generator[Union[IPv4Address, IPv6Address], None, None]:
        for network in self.data:
            yield from network.hosts()

    def supernet_of(self, other: Union[IPv4Address, IPv6Address, IPv4Network, IPv6Network]) -> bool:
        return any(n.supernet_of(other) for n in self.data)
