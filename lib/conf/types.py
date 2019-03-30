from abc import ABC, abstractmethod
from pydantic import validator
from pydantic.types import conint
from pydantic.dataclasses import dataclass
import builtins
import operator

from lib.conf.base import str_to_list

from typing import Iterable, Callable, Type, Any


def in_(a, b):
    return a in b


Port = conint(ge=0, le=65335)


@dataclass
class CallableFromString(Callable):
    _strings_to_callables = {}
    callable: Callable

    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)

    @validator('callable', pre=True)
    def adapt_callable(cls, v):
        name = cls.__name__.lower()
        if isinstance(v, str):
            try:
                return cls._strings_to_callables[v]
            except KeyError:
                raise TypeError(f"{v} not found")
        if not hasattr(cls._obj, v):
            raise TypeError(f"{v} not a valid {name}")
        return v


class Builtin(CallableFromString):
    _strings_to_callables = builtins.__dict__


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


class BaseSwappable(ABC):
    @abstractmethod
    def swap_cls(self, name) -> Type:
        pass


class RawStr(str):
    config_kwargs = {'raw': True}


class Expression:
    config_from_section = False
    attr: str
    op: Operator
    value_type: Builtin
    value: Any

    @validator('value')
    def adapt_value(cls, v, values, **kwargs):
        value_type = values['value_type']
        if issubclass(value_type, Iterable) and isinstance(v, str):
            v = str_to_list.split(v)
        return value_type(v)

    def test(self, obj):
        if not self.attr or self.attr == 'self':
            value = obj
        else:
            value = getattr(obj, self.attr)
        return self.op(value, self.value)
