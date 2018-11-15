import asyncio
import logging
import concurrent.futures
import settings

logger = logging.getLogger(settings.LOGGER_NAME)

class BaseTaskExecutor:

    def __init__(self, max_workers=None): ...

    async def run(self, func, *args):
        raise NotImplementedError


class TaskExecutor:

    async def run(self, func, *args):
        return func(*args)


class ThreadedTaskExecutor:
    executor_cls = concurrent.futures.ThreadPoolExecutor

    def __init__(self, max_workers=None):
        self.executor = self.executor_cls(max_workers=max_workers)

    async def run(self, func, *args):
        return asyncio.get_event_loop().run_in_executor(self.executor, func, *args)


class ProcessTaskExecutor:
    executor_cls = concurrent.futures.ProcessPoolExecutor
