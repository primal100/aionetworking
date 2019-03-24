import asyncio
from collections import ChainMap

from lib import settings
from lib.conf.logging import Logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseReceiver:
    receiver_type: str = ''
    logger_name: str = 'Receiver'
    configurable = {
        'quiet': bool,
    }

    @classmethod
    def get_config(cls, cp=None, logger_name=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Receiver', **cls.configurable)
        logger_name = logger_name or cls.logger_name
        logger = Logger(logger_name)
        logger.debug('Found configuration for %s: %s', cls.receiver_type, config)
        config.update(kwargs)
        config['logger'] = logger
        return config

    @classmethod
    def from_config(cls, manager: BaseMessageManager, cp=None, **kwargs):
        config = cls.get_config(cp=cp)
        return cls(manager, **config, **kwargs)

    def __init__(self, manager, quiet: bool=False, logger=None):
        self.quiet = quiet
        self.logger = logger or Logger(self.logger_name)
        self.manager = manager

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

    async def run(self):
        raise NotImplementedError

    async def wait_stopped(self):
        pass


class BaseServer(BaseReceiver):
    configurable = ChainMap(BaseReceiver.configurable, {
        'host': str,
        'port': int,
    })
    receiver_type = 'Server'
    server = None

    def __init__(self, *args, host: str = '0.0.0.0', port: int=4000, **kwargs):
        super(BaseServer, self).__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.listening_on = '%s:%s' % (self.host, self.port)

    def print_listening_message(self, sockets):
        if not self.quiet:
            for socket in sockets:
                sock_name = socket.getsockname()
                listening_on = ':'.join([str(v) for v in sock_name])
                print('Serving %s on %s' % (self.receiver_type, listening_on))

    async def close(self):
        self.logger.info('Stopping %s running at %s', self.receiver_type, self.listening_on)
        await self.stop_server()
        self.logger.info('%s stopped', self.receiver_type)

    async def run(self):
        self.logger.info('Starting %s on %s', self.receiver_type, self.listening_on)
        await self.start_server()

    async def stop_server(self):
        raise NotImplementedError

    async def start_server(self):
        raise NotImplementedError

    async def started(self):
        while not self.server or not self.server.is_serving():
            await asyncio.sleep(0.01)

    async def stopped(self):
        if self.server:
            await self.server.wait_closed()
