from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
import warnings

from lib.conf.logging import Logger
from lib.conf.types import LoggerType
from lib.formats.base import BaseMessageObject
from lib.utils import dataclass_getstate, dataclass_setstate

from typing import Iterator, List, Any, AnyStr, TypeVar, Type


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


ActionType = TypeVar('ActionType', bound='BaseAction')


@dataclass
class BaseAction(ABC):
    name = 'receiver action'
    logger: LoggerType = Logger('receiver.actions')

    timeout: int = 5

    @classmethod
    def swap_cls(cls, name: str) -> Type[ActionType]:
        from lib.definitions import ACTIONS
        return ACTIONS[name]

    def __post_init__(self) -> None:
        self.logger = self.logger.get_child(name='actions')

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def filter(self, msg: BaseMessageObject) -> bool:
        return msg.filter()

    async def close(self) -> None: ...

    def on_decode_error(self, data: AnyStr, exc: BaseException) -> Any:
        pass

    def on_exception(self, msg: BaseMessageObject, exc: BaseException) -> Any:
        pass

    async def do_one(self, msg: BaseMessageObject) -> Any: ...


