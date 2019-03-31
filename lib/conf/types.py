import logging
from pydantic import validator, BaseModel
from pydantic.types import conint
from pydantic.dataclasses import dataclass
from collections import ChainMap
import builtins
import operator

from lib.conf.base import str_to_list

from typing import Union, Callable, Iterable, Any


def in_(a, b):
    return a in b


Port = conint(ge=0, le=65335)


class Logger(logging.Logger):
    @classmethod
    def validate(cls, value: Union[str, logging.Logger]) -> logging.Logger:
        if isinstance(value, str):
            return logging.getLogger(value)
        return value


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
    _strings_to_callables = ChainMap(builtins.__dict__, {'istr': str})


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


class RawStr(str):
    config_kwargs = {'raw': True}


class Expression(BaseModel):
    config_from_string = True
    attr: str
    op: Operator
    value_type: Builtin
    value: Any
    case_sensitive: bool = True

    @validator('value')
    def adapt_value(cls, v, values, **kwargs):
        value_type = values['value_type']
        if issubclass(value_type, Iterable) and isinstance(v, str):
            v = str_to_list.split(v)
        return value_type(v)

    @validator('case_sensitive')
    def case_sensitive(cls, v, values, **kwargs):
        value_type = values['value_type']
        if value_type == 'istr':
            return False
        return True

    def __call__(self, obj):
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
