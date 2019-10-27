from __future__ import annotations
from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field

from .exceptions import ServerException
from aionetworking.conf.context import context_cv
from aionetworking.conf.logging import Logger, logger_cv, get_logger_receiver
from aionetworking.futures.value_waiters import StatusWaiter
from aionetworking.types.networking import ProtocolFactoryType
from aionetworking.utils import dataclass_getstate, dataclass_setstate, run_in_loop
from .protocols import ReceiverProtocol

from aionetworking.compatibility import Protocol


@dataclass
class BaseReceiver(ReceiverProtocol, Protocol):
    name = 'receiver'
    quiet: bool = False
    logger: Logger = field(default_factory=get_logger_receiver)
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        return dataclass_setstate(self, state)

    @run_in_loop
    async def serve_in_loop(self) -> None:
        await self.start()


@dataclass
class BaseServer(BaseReceiver, Protocol):
    name = 'Server'
    peer_prefix = 'server'

    protocol_factory:  ProtocolFactoryType = None
    server: asyncio.AbstractServer = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.protocol_factory.set_logger(self.logger)
        self.protocol_factory.set_name(self.full_name, self.peer_prefix)

    @property
    @abstractmethod
    def listening_on(self) -> str: ...

    @property
    def full_name(self):
        return f"{self.name} {self.listening_on}"

    def _print_listening_message(self) -> None:
        sockets = self.server.sockets
        for sock in sockets:
            sock_name = sock.getsockname()
            if isinstance(sock_name, (tuple, list)):
                listening_on = ':'.join([str(v) for v in sock_name])
            else:
                listening_on = sock_name
            print(f"Serving {self.name} on {listening_on}")

    async def start(self) -> None:
        if self._status.is_starting_or_started():
            raise ServerException(f"{self.name} running on {self.listening_on} already started")
        self._status.set_starting()
        context_cv.set({'endpoint': self.full_name})
        logger_cv.set(self.logger)
        await self.protocol_factory.start()
        self.logger.info('Starting %s on %s', self.name, self.listening_on)
        await self._start_server()
        if not self.quiet:
            self._print_listening_message()
        self._status.set_started()

    async def close(self) -> None:
        if self._status.is_stopping_or_stopped():
            raise ServerException(f"{self.name} running on {self.listening_on} already stopping or stopped")
        self._status.set_stopping()
        self.logger.info('Stopping %s running at %s', self.name, self.listening_on)
        await self._stop_server()
        self.logger.info('%s stopped', self.name)
        await self.protocol_factory.close()
        self._status.set_stopped()

    def close_all_connections(self) -> None:
        self.protocol_factory.close_all_connections(None)

    async def wait_num_connections(self, num: int):
        await self.protocol_factory.wait_num_connected(num)

    async def wait_num_has_connected(self, num: int):
        await self.protocol_factory.wait_num_has_connected(num)

    async def wait_all_connections_closed(self):
        await self.protocol_factory.wait_all_closed()

    async def wait_all_tasks_done(self) -> None:
        await self.protocol_factory.close_actions()

    def is_started(self) -> bool:
        return self._status.is_started()

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped()

    async def wait_started(self):
        await self._status.wait_started()

    async def wait_has_started(self):
        await self._status.wait_has_started()

    async def wait_stopped(self):
        await self._status.wait_stopped()

    @abstractmethod
    async def _get_server(self) -> asyncio.AbstractServer: ...

    async def _start_server(self) -> None:
        self.server = await self._get_server()

    async def _stop_server(self) -> None:
        self.server.close()
        await self.server.wait_closed()


@dataclass
class BaseNetworkServer(BaseServer, Protocol):
    host: str = '0.0.0.0'
    port: int = 4000

    @property
    def listening_on(self) -> str:
        return f"{self.host}:{self.port}"
