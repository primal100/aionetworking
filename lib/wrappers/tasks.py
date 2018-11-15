import asyncio
import logging

import settings
from .events import AsyncEventWrapper
from .queues import AsyncQueueWrapper
from lib.conf import ConfigurationException
from .twoway import TaskRunner, ThreadedTaskRunner

logger = logging.getLogger(settings.LOGGER_NAME)


class TaskWrapper:

    def __init__(self, cls, stop_event=None, started_event=None, stopped_event=None, *args, **kwargs):
        self.stop_event = stop_event or asyncio.Event()
        self.started_event = started_event or asyncio.Event()
        self.stopped_event = stopped_event or asyncio.Event()
        self.task = asyncio.create_task(self.start_task(cls, *args, **kwargs))

    async def start_task(self, cls, *args, **kwargs):
        logger.debug('Starting task')
        async with cls(args, **kwargs) as c:
            await asyncio.wait([c.run(self.started), self.stop_event.wait()], return_when=asyncio.FIRST_COMPLETED)
        logger.debug('Task stopped')
        self.stopped_event.set()

    async def started(self):
        await self.started_event.wait()

    async def stopped(self):
        await self.stopped_event.wait()

    def cancel(self):
        self.stop_event.set()


class ExecutorTaskWrapper(TaskWrapper):

    def __init__(self, executor, stop_event, queue, callback, *args):
        self.executor = executor
        self.stop_event = stop_event
        super(ExecutorTaskWrapper, self).__init__(queue, callback, *args)

    async def run(self):
        logger.debug('Running task in executor')
        await asyncio.get_running_loop().run_in_executor(
            self.executor, self.start_loop_in_executor)

    def start_loop_in_executor(self):
        asyncio.run(self.start_task())


