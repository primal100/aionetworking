from dataclasses import dataclass, field

from aionetworking.compatibility import Protocol
from aionetworking.logging.loggers import get_logger_receiver
from aionetworking.types.logging import LoggerType
from aionetworking.types.formats import MessageObjectType
from aionetworking.futures.value_waiters import StatusWaiter
from aionetworking.utils import dataclass_getstate, dataclass_setstate

from typing import Any, TypeVar, AsyncGenerator


ActionType = TypeVar('ActionType', bound='BaseAction')


@dataclass
class BaseAction(Protocol):
    supports_notifications = False
    name = 'receiver action'
    logger: LoggerType = field(default_factory=get_logger_receiver, metadata={'pickle': True})
    _status: StatusWaiter = field(default_factory=StatusWaiter, compare=False, repr=False)

    timeout: int = 5

    def _set_logger(self, logger: LoggerType = None) -> None:
        parent_logger = logger or self.logger
        self.logger = parent_logger.get_child(name='actions')

    async def start(self, logger: LoggerType = None) -> None:
        self._set_logger(logger=logger)

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def filter(self, msg: MessageObjectType) -> bool:
        return msg.filter()

    async def get_notifications(self, peer: str) -> AsyncGenerator[None, None]:
        yield

    def is_closing(self) -> None:
        return self._status.is_stopping_or_stopped()

    async def close(self) -> None:
        self._status.set_stopped()

    def on_decode_error(self, data: bytes, exc: BaseException) -> Any:
        pass

    def on_exception(self, msg: MessageObjectType, exc: BaseException) -> Any:
        pass

    async def do_one(self, msg: MessageObjectType) -> Any: ...


@dataclass
class EmptyAction(BaseAction): ...