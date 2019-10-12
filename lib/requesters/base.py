from .protocols import RequesterProtocol
from lib.compatibility import Protocol


class BaseRequester(RequesterProtocol, Protocol):
    async def start(self): ...

    async def close(self): ...

