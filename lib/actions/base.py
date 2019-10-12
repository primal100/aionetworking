from __future__ import annotations
from dataclasses import dataclass, field, InitVar
import warnings

from lib.compatibility import Protocol
from lib.conf.logging import Logger
from lib.conf.types import LoggerType
from lib.formats.types import MessageObjectType
from lib.wrappers.value_waiters import StatusWaiter
from lib.utils import dataclass_getstate, dataclass_setstate

from typing import Any, TypeVar, Type, AsyncGenerator


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


ActionType = TypeVar('ActionType', bound='BaseAction')


@dataclass
class BaseAction(Protocol):
    supports_notifications = False
    name = 'receiver action'
    logger: InitVar[LoggerType] = Logger('receiver')
    _status: StatusWaiter = field(default_factory=StatusWaiter, compare=False, repr=False)

    timeout: int = 5

    @classmethod
    def swap_cls(cls, name: str) -> Type[ActionType]:
        from lib.definitions import ACTIONS
        return ACTIONS[name]

    def __post_init__(self, logger) -> None:
        self.logger = logger.get_child(name='actions')

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def filter(self, msg: MessageObjectType) -> bool:
        return msg.filter()

    async def get_notifications(self) -> AsyncGenerator[None, None]:
        yield

    async def start(self) -> None: ...

    def is_closing(self) -> None:
        return self._status.is_stopping_or_stopped()

    async def close(self) -> None: ...

    def on_decode_error(self, data: bytes, exc: BaseException) -> Any:
        pass

    def on_exception(self, msg: MessageObjectType, exc: BaseException) -> Any:
        pass

    async def do_one(self, msg: MessageObjectType) -> Any: ...

