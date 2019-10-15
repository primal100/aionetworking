from __future__ import annotations
from abc import abstractmethod
import warnings

from lib.formats.types import MessageObjectType

from typing import AsyncGenerator, Any, AnyStr, TypeVar
from lib.compatibility import Protocol


warnings.filterwarnings("ignore", message="fields may not start with an underscore")


ActionType = TypeVar('ActionType', bound='BaseActionProtocol')


class ActionProtocol(Protocol):
    supports_notifications = False

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
    async def start(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
