import asyncio
import logging

from lib import settings

logger = logging.getLogger(settings.LOGGER_NAME)


class AsyncQueueWrapper:
    wrapped = True

    def __init__(self, queue):
        self.queue = queue

    def __getattr__(self, item):
        return getattr(self.queue, item)

    async def get(self):
        value = await asyncio.get_running_loop().run_in_executor(None, self.queue.get)
        return value[0]

    async def put(self, *args):
        return await asyncio.get_running_loop().run_in_executor(None, self.queue.put, args)

    async def join(self):
        return await asyncio.get_running_loop().run_in_executor(None, self.queue.join)
