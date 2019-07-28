from __future__ import annotations
from abc import abstractmethod
import warnings

from lib.conf.logging import Logger
from lib.formats.base import BaseMessageObject

from typing import Iterator, List, Any, AnyStr, TypeVar, Type
from typing_extensions import Protocol


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


ActionType = TypeVar('ActionType', bound='BaseActionProtocol')


class BaseActionProtocol(Protocol):

    @abstractmethod
    def filter(self, msg: BaseMessageObject) -> bool: ...

    @abstractmethod
    async def close(self) -> None: ...


class ParallelAction(BaseActionProtocol, Protocol):
    async def asnyc_do_one(self, msg: BaseMessageObject) -> Any: ...

    @abstractmethod
    def response_on_decode_error(self, data: AnyStr, exc: BaseException) -> Any: ...

    @abstractmethod
    def response_on_exception(self, msg: BaseMessageObject, exc: BaseException) -> Any: ...


class OneWaySequentialAction(BaseActionProtocol, Protocol):
    def do_one(self, msg: BaseMessageObject) -> Any: ...

    def do_many(self, msgs: Iterator[BaseMessageObject]):
        for msg in msgs:
            if not self.filter(msg):
                self.do_one(msg)
