from __future__ import annotations
from abc import abstractmethod
import asyncio

from dataclasses import dataclass, field
from lib.types import Logger
from lib.networking.types import ConnectionGeneratorType, ConnectionType

from typing import Tuple
from typing_extensions import Protocol


@dataclass
class BaseSender(Protocol):
    name = 'sender'
    logger: Logger = 'sender'

    @property
    def loop(self) -> asyncio.SelectorEventLoop:
        return asyncio.get_event_loop()

    async def __aenter__(self) -> ConnectionType:
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    @abstractmethod
    async def start(self) -> ConnectionType: ...

    async def stop(self):
        pass


@dataclass
class BaseNetworkClient(BaseSender):
    name = "Network client"
    conn: ConnectionType = field(init=False)
    transport: asyncio.BaseTransport = field(init=False, compare=False)

    host: str = '127.0.0.1'
    port: int = 4000
    srcip: str = None
    srcport: int = 0
    protocol_generator:  ConnectionGeneratorType = None

    @abstractmethod
    async def open_connection(self) -> ConnectionType: ...

    async def close_connection(self):
        self.transport.close()

    @property
    def local_addr(self) -> Tuple[str, int]:
        return self.srcip, self.port

    @property
    def dst(self):
        return f"{self.host}:{str(self.port)}"

    async def start(self) -> ConnectionType:
        self.logger.info("Opening %s connection to %s", self.name, self.dst)
        connection = await self.open_connection()
        return connection

    async def stop(self) -> None:
        self.logger.info("Closing %s connection to %s", self.name, self.dst)
        await self.close_connection()
