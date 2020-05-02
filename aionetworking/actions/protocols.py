from abc import abstractmethod
from dataclasses import dataclass

from aionetworking.types.formats import MessageObjectType
from aionetworking.types.logging import LoggerType

from typing import AsyncGenerator, Any, TypeVar
from aionetworking.compatibility import Protocol


ActionType = TypeVar('ActionType', bound='BaseActionProtocol')


@dataclass
class ActionProtocol(Protocol):
    supports_notifications = False
    task_timeout: int = 10

    @abstractmethod
    def filter(self, msg: MessageObjectType) -> bool: ...

    @abstractmethod
    async def do_one(self, msg: MessageObjectType) -> Any: ...

    @abstractmethod
    def on_decode_error(self, data: bytes, exc: BaseException) -> Any: ...

    @abstractmethod
    def on_exception(self, msg: MessageObjectType, exc: BaseException) -> Any: ...

    @abstractmethod
    async def get_notifications(self, peer: str) -> AsyncGenerator[None, None]:
        yield

    @abstractmethod
    async def start(self, logger: LoggerType = None) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

