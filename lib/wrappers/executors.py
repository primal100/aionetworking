import asyncio
import logging
import concurrent.futures
from lib import settings

logger = logging.getLogger(settings.LOGGER_NAME)

class BaseTaskExecutor:

    def __init__(self, max_workers=None): ...

    async def run(self, func, *args):
        raise NotImplementedError

    async def run_coroutine(self, coro):
        raise NotImplementedError


class TaskExecutor:

    async def run(self, func, *args):
        return func(*args)


class ThreadedTaskExecutor:
    executor_cls = concurrent.futures.ThreadPoolExecutor

    def __init__(self, max_workers=None):
        self.executor = self.executor_cls(max_workers=max_workers)
        self.loop = asyncio.get_event_loop()

    async def run(self, func, *args):
        return await self.loop.run_in_executor(self.executor, func, *args)


class ProcessTaskExecutor(ThreadedTaskExecutor):
    executor_cls = concurrent.futures.ProcessPoolExecutor
