from __future__ import annotations
from dataclasses import dataclass, field
import warnings

from aionetworking.compatibility import Protocol
from aionetworking.logging.loggers import logger_cv
from aionetworking.types.logging import LoggerType
from aionetworking.types.formats import MessageObjectType
from aionetworking.futures.value_waiters import StatusWaiter
from aionetworking.utils import dataclass_getstate, dataclass_setstate

from typing import Any, TypeVar, AsyncGenerator


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


ActionType = TypeVar('ActionType', bound='BaseAction')


@dataclass
class BaseAction(Protocol):
    supports_notifications = False
    name = 'receiver action'
    logger: LoggerType = field(default_factory=logger_cv.get)
    _status: StatusWaiter = field(default_factory=StatusWaiter, compare=False, repr=False)

    timeout: int = 5

    def set_logger(self, logger: LoggerType) -> None:
        self.logger = logger.get_child(name='actions')

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def filter(self, msg: MessageObjectType) -> bool:
        return msg.filter()

    async def get_notifications(self, peer: str) -> AsyncGenerator[None, None]:
        yield

    async def start(self) -> None: ...

    def is_closing(self) -> None:
        return self._status.is_stopping_or_stopped()

    async def close(self) -> None:
        self._status.is_stopped()

    def on_decode_error(self, data: bytes, exc: BaseException) -> Any:
        pass

    def on_exception(self, msg: MessageObjectType, exc: BaseException) -> Any:
        pass

    async def do_one(self, msg: MessageObjectType) -> Any: ...


@dataclass
class EmptyAction(BaseAction): ...