from __future__ import annotations
from abc import abstractmethod
import asyncio

from dataclasses import dataclass, field, replace

from pathlib import Path
from typing import Tuple, Sequence, AnyStr
from aionetworking.compatibility import Protocol
from aionetworking.logging.loggers import logger_cv, get_logger_sender
from aionetworking.types.logging import LoggerType
from aionetworking.types.networking import ProtocolFactoryType, ConnectionType
from aionetworking.utils import addr_tuple_to_str, dataclass_getstate, dataclass_setstate, run_in_loop, get_ip_port
from aionetworking.futures.value_waiters import StatusWaiter
from aionetworking.networking.connections_manager import get_unique_name
from .protocols import SenderProtocol

from typing import Optional


@dataclass
class BaseSender(SenderProtocol, Protocol):
    name = 'sender'
    logger: LoggerType = field(default_factory=get_logger_sender)
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

    def is_started(self) -> bool:
        return self._status.is_started()

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped()

    async def wait_stopped(self) -> None:
        await self._status.wait_stopped()


@dataclass
class BaseClient(BaseSender, Protocol):
    expected_connection_exceptions = (ConnectionRefusedError,)
    name = "Client"
    peer_prefix = ''
    protocol_factory:  ProtocolFactoryType = None
    conn: ConnectionType = field(init=False, default=None)
    transport: Optional[asyncio.BaseTransport] = field(init=False, compare=False, default=None)
    timeout: int = 5

    def __post_init__(self):
        self.protocol_factory.set_logger(self.logger)
        self.protocol_factory = replace(self.protocol_factory)
        self._full_name = get_unique_name(self.full_name)
        self.protocol_factory.set_name(self._full_name, self.peer_prefix)

    @abstractmethod
    async def _open_connection(self) -> ConnectionType: ...

    @property
    @abstractmethod
    def src(self) -> str: ...

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.dst}"

    async def _close_connection(self) -> None:
        self.transport.close()
        await self.conn.wait_closed()
        self.transport = None

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped() or self.transport.is_closing()

    async def connect(self) -> ConnectionType:
        self._status.set_starting()
        logger_cv.set(self.logger)
        await self.protocol_factory.start()
        self.logger.info("Opening %s connection to %s", self.name, self.dst)
        connection = await self._open_connection()
        connection.add_connection_lost_task(self.on_connection_lost)
        await connection.wait_connected()
        self._status.set_started()
        return connection

    async def on_connection_lost(self) -> None:
        if not self._status.is_stopping_or_stopped():
            self.logger.info('%s connection to %s was closed on the other end', self.name, self.dst)
            self._status.set_stopping()
            await self.protocol_factory.close()
            self._status.set_stopped()

    async def close(self) -> None:
        self._status.set_stopping()
        self.logger.info("Closing %s connection to %s", self.name, self.dst)
        await self._close_connection()
        await self.protocol_factory.close()
        self._status.set_stopped()

    @run_in_loop
    async def open_send_msgs(self, msgs: Sequence[AnyStr], interval: int = None, start_interval: int = 0,
                             override: dict = None, wait_responses: bool = False) -> None:
        if override:
            for k, v in override.items():
                setattr(self, k, v)
        async with self as conn:
            await asyncio.sleep(start_interval)
            for msg in msgs:
                if interval is not None:
                    await asyncio.sleep(interval)
                conn.send_data(msg)
            if wait_responses:
                for _ in msgs:
                    await conn.wait_notification()
            await asyncio.sleep(0.1) ##Workaround for bpo-38471

    @run_in_loop
    async def open_play_recording(self, path: Path, hosts: Sequence = (), timing: bool = True) -> None:
        async with self as conn:
            await conn.play_recording(path, hosts=hosts, timing=timing)


@dataclass
class BaseNetworkClient(BaseClient, Protocol):
    name = "Network Client"

    host: str = '127.0.0.1'
    port: int = 4000
    srcip: str = None
    srcport: int = 0
    _actual_src: Optional[Tuple[str, int]] = field(default=None, init=False, repr=False)

    @property
    def local_addr(self) -> Optional[Tuple[str, int]]:
        if self.srcip:
            return self.srcip, self.srcport
        return None

    @property
    def actual_local_addr(self) -> Tuple[str, int]:
        if self.host and self.transport:
            self._actual_listening_on = get_ip_port(self.host, self.transport)
            return self._actual_listening_on
        if self._actual_listening_on:
            return self._actual_listening_on

    @property
    def src(self) -> str:
        return addr_tuple_to_str(self.actual_local_addr)

    @property
    def dst(self) -> str:
        return f"{self.host}:{str(self.port)}"