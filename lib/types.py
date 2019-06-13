import logging
from collections import ChainMap#
from pathlib import Path
import builtins
import operator

from pydantic import validator, errors, BaseModel, ValidationError
from pydantic.types import conint
from pydantic.validators import path_validator
from pydantic.utils import AnyCallable

from lib.utils import str_to_list

from typing import TYPE_CHECKING, Union, Generator, Callable, Iterable, Any


if TYPE_CHECKING:
    from dataclasses import dataclass
    from typing import Type
    CallableGenerator = Generator[AnyCallable, None, None]
else:
    from pydantic.dataclasses import dataclass
    class Type:
        base_cls = None

        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, value):
            if isinstance(value, str):
                return cls.base_cls.swap_cls(str)
            if issubclass(value, cls.base_cls):
                return cls.base_cls
            raise ValidationError(f"{value} is not a subclass of {cls.base_cls}")

        def __class_getitem__(cls, item):
            return type(f"{item.__name__}Type", (cls,), {'base_cls': item})


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
        if v not in cls._strings_to_callables.values():
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


class RawStr(str):
    config_kwargs = {'raw': True}


@dataclass
class Expression:
    config_from_string = True
    attr: str
    op: Operator
    value_type: Builtin
    value: Any
    case_sensitive: bool = True

    @validator('value')
    def adapt_value(cls, v: Any, values: dict) -> Any:
        value_type = values['value_type']
        if issubclass(value_type, Iterable) and isinstance(v, str):
            v = str_to_list.split(v)
        return value_type(v)

    @validator('case_sensitive')
    def case_sensitive(cls, v: bool, values: dict) -> bool:
        value_type = values['value_type']
        if value_type == 'istr':
            return False
        return True

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
