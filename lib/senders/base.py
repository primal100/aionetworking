from __future__ import annotations
from abc import abstractmethod
import asyncio

from dataclasses import dataclass, field
from lib.conf.logging import Logger
from lib.networking.types import ProtocolFactoryType, ConnectionType

from typing import Tuple
from lib.compatibility import Protocol
from lib.utils import addr_tuple_to_str, dataclass_getstate, dataclass_setstate
from .protocols import SenderProtocol


@dataclass
class BaseSender(SenderProtocol, Protocol):
    name = 'sender'
    logger: Logger = Logger('sender')

    @property
    def loop(self) -> asyncio.SelectorEventLoop:
        return asyncio.get_event_loop()

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        return dataclass_setstate(self, state)

    async def __aenter__(self) -> ConnectionType:
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self):
        pass


@dataclass
class BaseClient(BaseSender, Protocol):
    name = "Client"
    peer_prefix = ''
    protocol_factory:  ProtocolFactoryType = None
    conn: ConnectionType = field(init=False, default=None)
    transport: asyncio.BaseTransport = field(init=False, compare=False, default=None)
    timeout: int = 5

    def __post_init__(self):
        self.logger.update_extra(endpoint=self.full_name)
        self.protocol_factory.set_logger(self.logger)
        self.protocol_factory.set_name(self.full_name, self.peer_prefix)

    @abstractmethod
    async def _open_connection(self) -> ConnectionType: ...

    @property
    @abstractmethod
    def src(self) -> str: ...

    @property
    def full_name(self):
        return f"{self.name}_{self.src}"

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
    def src(self) -> str:
        return addr_tuple_to_str(self.local_addr)

    @property
    def dst(self) -> str:
        return f"{self.host}:{str(self.port)}"
