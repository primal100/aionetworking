from __future__ import annotations
from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field

from .exceptions import ServerException
from lib.conf.logging import Logger
from lib.networking.types import ProtocolFactoryType
from lib.factories import event_set
from .protocols import ReceiverProtocol

from lib.compatibility import Protocol


@dataclass
class BaseReceiver(ReceiverProtocol, Protocol):
    name = 'receiver'
    logger: Logger = 'receiver'
    quiet: bool = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    async def start_wait(self) -> bool:
        await self.start()
        return await self.wait_started()

    async def stop_wait(self) -> bool:
        await self.stop()
        return await self.wait_stopped()


@dataclass
class BaseServer(BaseReceiver, Protocol):
    name = 'Server'

    protocol_factory:  ProtocolFactoryType = None
    server: asyncio.AbstractServer = field(default=None, init=False)
    started: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    stopped: asyncio.Event = field(default_factory=event_set, init=False)

    @property
    @abstractmethod
    def listening_on(self) -> str: ...

    def _print_listening_message(self) -> None:
        sockets = self.server.sockets
        for sock in sockets:
            sock_name = sock.getsockname()
            listening_on = ':'.join([str(v) for v in sock_name])
            print(f"Serving {self.name} on {listening_on}")

    async def stop(self) -> None:
        if self.stopped.is_set():
            raise ServerException(f"{self.name} running on {self.listening_on} already stopped")
        if not self.started.is_set():
            raise ServerException(f"{self.name} running on {self.listening_on} not yet started")
        self.logger.info('Stopping %s running at %s', self.name, self.listening_on)
        self.started.clear()
        await self.stop_server()
        self.logger.info('%s stopped', self.name)
        await self.protocol_factory.wait_all_closed()
        self.stopped.set()

    async def start(self) -> None:
        if self.started.is_set():
            raise ServerException(f"{self.name} running on {self.listening_on} already started")
        self.logger.info('Starting %s on %s', self.name, self.listening_on)
        self.stopped.clear()
        await self.start_server()
        if not self.quiet:
            self._print_listening_message()
        self.started.set()

    def _is_serving(self) -> bool:
        return self.server.is_serving()

    def is_started(self) -> bool:
        return self.started.is_set() and self._is_serving()

    async def wait_started(self) -> bool:
        await self.started.wait()
        return self._is_serving()

    async def wait_stopped(self) -> bool:
        await self.stopped.wait()
        return self._is_serving()

    @abstractmethod
    async def _get_server(self) -> asyncio.AbstractServer: ...

    async def start_server(self) -> None:
        self.server = await self._get_server()

    async def stop_server(self) -> None:
        self.server.close()
        await self.server.wait_closed()


@dataclass
class BaseNetworkServer(BaseServer, Protocol):
    host: str = '0.0.0.0'
    port: int = 4000

    @property
    def listening_on(self) -> str:
        return f"{self.host}:{self.port}"
