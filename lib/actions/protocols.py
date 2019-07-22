from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass, field
import warnings

from lib.conf.logging import Logger
from lib.formats.base import BaseMessageObject

from typing import Iterator, List, Any, AnyStr, TypeVar, Type
from typing_extensions import Protocol      #3.8


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


ActionType = TypeVar('ActionType', bound='BaseAction')


@dataclass
class BaseActionProtocol(Protocol):
    name = 'receiver action'
    logger: Logger = Logger('receiver')

    timeout: int = 5
    _outstanding_tasks: List = field(default_factory=list, init=False, repr=False, hash=False)

    @classmethod
    def swap_cls(cls, name: str) -> Type[ActionType]:
        from lib.definitions import ACTIONS
        return ACTIONS[name]

    def __post_init__(self) -> None:
        self.logger = self.logger.get_child(name='actions')

    def filter(self, msg: BaseMessageObject) -> bool:
        return msg.filter()

    async def close(self) -> None: ...

    def response_on_decode_error(self, data: AnyStr, exc: BaseException) -> Any:
        pass

    def response_on_exception(self, msg: BaseMessageObject, exc: BaseException) -> Any:
        pass


class ParallelAction(BaseActionProtocol, Protocol):
    async def asnyc_do_one(self, msg: BaseMessageObject) -> Any: ...


class SequentialAction(BaseActionProtocol, Protocol):
    def do_one(self, msg: BaseMessageObject) -> Any: ...

    def do_many(self, msgs: Iterator[BaseMessageObject]):
        for msg in msgs:
            if not self.filter(msg):
                self.do_one(msg)
