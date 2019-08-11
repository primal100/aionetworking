from __future__ import annotations
from abc import abstractmethod
from typing_extensions import Protocol


class ReceiverProtocol(Protocol):

    @abstractmethod
    async def wait_started(self) -> bool: ...

    @abstractmethod
    async def wait_stopped(self) -> bool: ...

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def stop(self): ...

    @abstractmethod
    def is_started(self) -> bool: ...

    @abstractmethod
    async def start_wait(self) -> bool: ...

    @abstractmethod
    async def stop_wait(self) -> bool: ...