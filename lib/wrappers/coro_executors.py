import asyncio
from concurrent import futures
import logging

from lib import settings
from lib.conf import ConfigurationException
from lib.wrappers.events import AsyncEventWrapper

logger = logging.getLogger(settings.LOGGER_NAME)


class TaskRunner:
    @classmethod
    def get_task_runner(cls, manager, run_as):
        if run_as == 'asyncio':
            return cls(manager)
        elif run_as == 'thread':
            return ThreadedTaskRunner()
        elif run_as == 'process':
            raise ConfigurationException(
                'Multiprocessing not supported for two-way communication. Available options are: asyncio, thread')

    def __init__(self, func, args):
        self.func = func
        self.args = args
        self.started_event = self.new_event()
        self.stopped_event = self.new_event()
        self.stop_event = self.new_event()



    def run_in_loop(self):
        await self.func(self.started_event, self.stopped_event, self.stop_event, *args)

    async def run(self):
        await self.run_in_loop()

    async def stopped(self):
        await self.stopped_event.wait()

    async def started(self):
        await self.started_event.wait()

    def stop(self):
        self.stop_event.set()


class ThreadedTaskRunner(TaskRunner):
    executor = futures.ThreadPoolExecutor

    def new_event(self):
        import threading
        return AsyncEventWrapper(threading.Event())

    def __init__(self, *args, **kwargs):
        super(ThreadedTaskRunner, self).__init__(*args, **kwargs)
        self.executor = self.executor_class(target=self.start)
        self.executor.start()
        self.loop = asyncio.new_event_loop()

    def start(self):
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop())

    def manage_item(self, item):
        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(self.manager.process(item), self.loop))


class ProcessTaskRunner(ThreadedTaskRunner):
    executor = futures.ProcessPoolExecutor

    def new_event(self):
        import multiprocessing
        return AsyncEventWrapper(multiprocessing.Event())
