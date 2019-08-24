from __future__ import annotations
from abc import abstractmethod
from lib.compatibility import Protocol


class ReceiverProtocol(Protocol):

    @abstractmethod
    async def wait_started(self): ...

    @abstractmethod
    async def wait_stopped(self): ...

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def close(self): ...

    @abstractmethod
    def is_started(self) -> bool: ...

    @abstractmethod
    def is_closing(self) -> bool: ...

    @abstractmethod
    async def wait_all_tasks_done(self) -> None: ...
