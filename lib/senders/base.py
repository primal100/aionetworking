from __future__ import annotations
from abc import abstractmethod
import asyncio

from dataclasses import dataclass, field
from lib.conf.logging import Logger
from lib.networking.types import ProtocolFactoryType, ConnectionType

from typing import Tuple
from lib.compatibility import Protocol


@dataclass
class BaseSender(Protocol):
    name = 'sender'
    logger: Logger = Logger('sender')

    @property
    def loop(self) -> asyncio.SelectorEventLoop:
        return asyncio.get_event_loop()

    async def __aenter__(self) -> ConnectionType:
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @abstractmethod
    def is_started(self) -> bool: ...

    @abstractmethod
    def is_closing(self) -> bool: ...

    @abstractmethod
    async def connect(self) -> ConnectionType: ...

    async def close(self):
        pass


@dataclass
class BaseClient(BaseSender, Protocol):
    name = "Client"
    protocol_factory:  ConnectionGeneratorType = None
    conn: ConnectionType = field(init=False, default=None)
    transport: asyncio.BaseTransport = field(init=False, compare=False, default=None)
    timeout: int =2

    @property
    @abstractmethod
    def dst(self) -> str: ...

    @abstractmethod
    async def _open_connection(self) -> ConnectionType: ...

    async def _close_connection(self):
        self.transport.close()
        await self.conn.close_wait()

    def is_started(self) -> bool:
        return bool(self.conn)

    def is_closing(self) -> bool:
        return not self.transport or self.transport.is_closing()

    async def connect(self) -> ConnectionType:
        self.logger.info("Opening %s connection to %s", self.name, self.dst)
        connection = await self._open_connection()
        await connection.wait_connected()
        return connection

    async def close(self) -> None:
        self.logger.info("Closing %s connection to %s", self.name, self.dst)
        await self._close_connection()


@dataclass
class BaseNetworkClient(BaseClient, Protocol):
    name = "Network client"

    host: str = '127.0.0.1'
    port: int = 4000
    srcip: str = None
    srcport: int = 0

    @property
    def local_addr(self) -> Tuple[str, int]:
        return self.srcip, self.srcport

    @property
    def dst(self) -> str:
        return f"{self.host}:{str(self.port)}"
