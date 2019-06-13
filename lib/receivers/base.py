from abc import ABC, abstractmethod
import asyncio

from lib.types import Logger, Port
from lib.networking.asyncio_protocols import BaseReceiverProtocol
from lib.networking.mixins import BaseServerProtocol

from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass


@dataclass
class BaseReceiver(ABC):
    name = 'receiver'
    logger: Logger = 'receiver'
    protocol: BaseReceiverProtocol = None

    quiet: bool = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    async def started(self) -> bool:
        return True

    async def stopped(self) -> bool:
        return True

    async def start(self) -> NoReturn:
        try:
            await self.run()
        except asyncio.CancelledError:
            self.logger.debug('Receiver task cancelled')
            await self.close()

    async def close(self) -> NoReturn:
        pass

    async def wait_stopped(self) -> NoReturn:
        pass

    @abstractmethod
    async def run(self) -> NoReturn: ...


@dataclass
class BaseServer(ABC, BaseReceiver):
    name = 'Server'
    server = None

    host: str = '0.0.0.0'
    port: Port = 4000
    protocol:  BaseServerProtocol = None

    @property
    def listening_on(self) -> str:
        return f"{self.host}:{self.port}"

    def print_listening_message(self, sockets) -> NoReturn:
        if not self.quiet:
            for socket in sockets:
                sock_name = socket.getsockname()
                listening_on = ':'.join([str(v) for v in sock_name])
                print(f"Serving, {self.name}, on {listening_on}")

    async def close(self) -> NoReturn:
        self.logger.info('Stopping %s running at %s', self.name, self.listening_on)
        await self.stop_server()
        await self.protocol.close()
        self.logger.info('%s stopped', self.name)

    async def started(self) -> NoReturn:
        while not self.server or not self.server.is_serving():
            await asyncio.sleep(0.01)

    async def stopped(self) -> NoReturn:
        if self.server:
            await self.server.wait_closed()

    async def run(self) -> NoReturn:
        self.logger.info('Starting %s on %s', self.name, self.listening_on)
        await self.start_server()

    @abstractmethod
    async def stop_server(self) -> NoReturn: ...

    @abstractmethod
    async def start_server(self) -> NoReturn: ...

