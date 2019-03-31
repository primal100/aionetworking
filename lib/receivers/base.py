import asyncio
import logging
from lib.conf.types import Logger, Port
from abc import ABC, abstractmethod


class BaseReceiver(ABC):
    name = 'receiver'
    logger: Logger = logging.getLogger('receiver')

    quiet: bool = False

    async def started(self):
        return True

    async def stopped(self):
        return True

    async def start(self):
        try:
            await self.run()
        except asyncio.CancelledError:
            self.logger.debug('Receiver task cancelled')
            await self.close()

    async def close(self):
        pass

    async def wait_stopped(self):
        pass

    @abstractmethod
    async def run(self): ...


class BaseServer(ABC, BaseReceiver):
    name = 'Server'
    server = None

    host: str = '0.0.0.0'
    port: Port = 4000

    @property
    def listening_on(self):
        return f"{self.host}:{self.port}"

    def print_listening_message(self, sockets):
        if not self.quiet:
            for socket in sockets:
                sock_name = socket.getsockname()
                listening_on = ':'.join([str(v) for v in sock_name])
                print('Serving %s on %s' % (self.name, listening_on))

    async def close(self):
        self.logger.info('Stopping %s running at %s', self.name, self.listening_on)
        await self.stop_server()
        self.logger.info('%s stopped', self.name)

    async def started(self):
        while not self.server or not self.server.is_serving():
            await asyncio.sleep(0.01)

    async def stopped(self):
        if self.server:
            await self.server.wait_closed()

    async def run(self):
        self.logger.info('Starting %s on %s', self.name, self.listening_on)
        await self.start_server()

    @abstractmethod
    async def stop_server(self): ...

    @abstractmethod
    async def start_server(self): ...

