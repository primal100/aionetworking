from collections import ChainMap
import builtins
import operator

from lib.utils import str_to_list

from typing import Union, Callable, Iterable, Any


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