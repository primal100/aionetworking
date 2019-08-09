from __future__ import annotations
from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field

from .exceptions import ServerException
from lib.conf.logging import Logger
from lib.networking.protocols import ConnectionGeneratorType
from .protocols import ReceiverProtocol

from socket import socket
from typing import List
from typing_extensions import Protocol


@dataclass
class BaseReceiver(ReceiverProtocol, Protocol):
    name = 'receiver'
    logger: Logger = 'receiver'
    quiet: bool = False

    def __post_init__(self):
        asyncio.create_task(self.start())

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()


@dataclass
class BaseServer(BaseReceiver, Protocol):
    name = 'Server'

    protocol_generator:  ConnectionGeneratorType = None
    server: asyncio.AbstractServer = field(default=None, init=False)
    started: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    stopped: asyncio.Event = field(default_factory=asyncio.Event, init=False)

    @property
    @abstractmethod
    def listening_on(self) -> str: ...

    def _print_listening_message(self, sockets) -> None:
        if not self.quiet:
            for sock in sockets:
                sock_name = sock.getsockname()
                listening_on = ':'.join([str(v) for v in sock_name])
                print(f"Serving, {self.name}, on {listening_on}")

    async def stop(self) -> None:
        if self.stopped.set():
            raise ServerException(f"{self.name} running on {self.listening_on} already stopped")
        if not self.started.set():
            raise ServerException(f"{self.name} running on {self.listening_on} not yet started")
        self.logger.info('Stopping %s running at %s', self.name, self.listening_on)
        await self.started.clear()
        await self.stop_server()
        self.logger.info('%s stopped', self.name)
        await self.protocol_generator.wait_all_closed()
        self.stopped.set()

    async def start(self) -> None:
        if self.started.set():
            raise ServerException(f"{self.name} running on {self.listening_on} already started")
        self.logger.info('Starting %s on %s', self.name, self.listening_on)
        self.stopped.clear()
        sockets = await self.start_server()
        self.started.set()
        self._print_listening_message(sockets)

    async def wait_started(self) -> None:
        await self.started.wait()

    async def wait_stopped(self) -> None:
        await self.stopped.wait()

    @abstractmethod
    async def stop_server(self) -> None: ...

    @abstractmethod
    async def start_server(self) -> List[socket]: ...


@dataclass
class BaseNetworkServer(BaseServer, Protocol):
    host: str = '0.0.0.0'
    port: int = 4000

    @property
    def listening_on(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class BaseTCPReceiver(BaseNetworkServer, Protocol):
    server: asyncio.AbstractServer = None

    @abstractmethod
    async def get_server(self) -> asyncio.AbstractServer: ...

    async def start_server(self) -> List[socket]:
        self.server = await self.get_server()
        return self.server.sockets

    async def stop_server(self) -> None:
        self.server.close()
        await self.server.wait_closed()
