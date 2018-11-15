import asyncio
import logging

import settings
from lib.conf import ConfigurationException

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

    def __init__(self, manager):
        self.manager = manager

    def stop(self): ...

    async def manage_item(self, item):
        await self.manager.process(item)



class ThreadedTaskRunner(TaskRunner):

    def __init__(self, *args, **kwargs):
        super(ThreadedTaskRunner, self).__init__(*args, **kwargs)
        self.executor = self.executor_class(target=self.start)
        self.executor.start()
        self.loop = asyncio.new_event_loop()

    @property
    def executor_class(self):
        import threading
        return threading.Thread

    def start(self):
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop())

    def manage_item(self, item):
        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(self.manager.process(item), self.loop))


class ProcessTaskRunner(ThreadedTaskRunner):

    @property
    def executor_class(self):
        import multiprocessing
        return multiprocessing.Process
