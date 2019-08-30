from __future__ import annotations
from abc import abstractmethod
import asyncio
import datetime
import os

from dataclasses import dataclass, field
from lib.networking.types import ProtocolFactoryType, ConnectionType

from pathlib import Path
from typing import Tuple, Sequence, AnyStr
from lib.compatibility import Protocol
from lib.conf.context import context_cv
from lib.conf.logging import Logger, logger_cv
from lib.utils import addr_tuple_to_str, dataclass_getstate, dataclass_setstate, run_in_loop
from lib.wrappers.value_waiters import StatusWaiter
from .protocols import SenderProtocol

from typing import Type


@dataclass
class BaseSender(SenderProtocol, Protocol):
    name = 'sender'
    logger_cls: Type[Logger] = Logger
    logger_name = 'sender'
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)

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

    def __post_init__(self):
        self.logger = self.logger_cls(self.logger_name)


@dataclass
class BaseClient(BaseSender, Protocol):
    name = "Client"
    peer_prefix = ''
    protocol_factory:  ProtocolFactoryType = None
    conn: ConnectionType = field(init=False, default=None)
    transport: asyncio.BaseTransport = field(init=False, compare=False, default=None)
    timeout: int = 5

    def __post_init__(self):
        super().__post_init__()
        self.protocol_factory.set_logger(self.logger)
        self.protocol_factory.set_name(self.full_name, self.peer_prefix)

    @abstractmethod
    async def _open_connection(self) -> ConnectionType: ...

    @property
    @abstractmethod
    def src(self) -> str: ...

    @property
    def full_name(self):
        return f"{self.name} {self.src}"

    async def _close_connection(self):
        self.conn.close()
        await self.conn.wait_closed()

    def is_started(self) -> bool:
        return self._status.is_started()

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped() or self.transport.is_closing()

    async def connect(self) -> ConnectionType:
        self._status.set_starting()
        context_cv.set({'endpoint': self.full_name})
        logger_cv.set(self.logger)
        await self.protocol_factory.start()
        self.logger.info("Opening %s connection to %s", self.name, self.dst)
        connection = await self._open_connection()
        await self.conn.wait_connected()
        self._status.set_started()
        return connection

    async def close(self) -> None:
        self._status.set_stopping()
        self.logger.info("Closing %s connection to %s", self.name, self.dst)
        await self._close_connection()
        self._status.set_stopped()

    @run_in_loop
    async def open_send_msgs(self, msgs: Sequence[AnyStr], interval: int = None, start_interval: int = 0,
                             override: dict = None) -> None:
        if override:
            for k, v in override.items():
                setattr(self, k, v)
        async with self as conn:
            self.logger.info('starting connection')
            await asyncio.sleep(start_interval)
            for msg in msgs:
                if interval is not None:
                    await asyncio.sleep(interval)
                conn.send_data(msg)
        self.logger.info('closing connection')

    @run_in_loop
    async def open_play_recording(self, path: Path, hosts: Sequence = (), timing: bool = True) -> None:
        async with self as conn:
            await conn.play_recording(path, hosts=hosts, timing=timing)


@dataclass
class BaseNetworkClient(BaseClient, Protocol):
    name = "Network client"

    host: str = '127.0.0.1'
    port: int = 4000
    srcip: str = None
    srcport: int = 0
    actual_srcip: str = field(default=None, init=False, compare=False)
    actual_srcport: int = field(default=None, init=False, compare=False)

    @property
    def local_addr(self) -> Tuple[str, int]:
        return self.srcip, self.srcport

    @property
    def actual_local_addr(self) -> Tuple[str, int]:
        return self.actual_srcip, self.actual_srcport

    @property
    def src(self) -> str:
        return addr_tuple_to_str(self.actual_local_addr)

    @property
    def dst(self) -> str:
        return f"{self.host}:{str(self.port)}"
