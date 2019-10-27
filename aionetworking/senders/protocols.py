from abc import abstractmethod
from aionetworking.compatibility import Protocol
from aionetworking.types.networking import ConnectionType


class SenderProtocol(Protocol):

    @property
    @abstractmethod
    def dst(self) -> str: ...

    @abstractmethod
    async def __aenter__(self) -> ConnectionType: ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...

    @abstractmethod
    def is_started(self) -> bool: ...

    @abstractmethod
    def is_closing(self) -> bool: ...

    @abstractmethod
    async def connect(self) -> ConnectionType: ...

    @abstractmethod
    async def close(self): ...