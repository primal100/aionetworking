from .base import BaseMessageManager
import asyncio
import threading
from queue import Queue
import settings
import logging

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseThreadedMessageManager(BaseMessageManager):

    def __init__(self, protocol, queue=None, *args, **kwargs):
        queue = queue or Queue()
        super(BaseMessageManager, self).__init__(protocol, queue, *args, **kwargs)

    def run_thread(self):
        import asyncio
        import definitions
        definitions.LOGGER_NAME = 'messagemanagerthreaded'
        asyncio.run(self.process_queue_later())

    async def add_to_queue(self, host, encoded, timestamp):
        self.queue.put((host, encoded, timestamp))

    async def close(self):
        pass
