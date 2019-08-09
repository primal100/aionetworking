from __future__ import annotations
from abc import abstractmethod
from typing_extensions import Protocol


class ReceiverProtocol(Protocol):

    @abstractmethod
    async def wait_started(self) -> None: ...

    @abstractmethod
    async def wait_stopped(self) -> None: ...

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def stop(self): ...