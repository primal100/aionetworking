import asyncio
from asyncio import Event
import logging

import settings
from lib.wrappers.events import AsyncEventWrapper

logger = logging.getLogger(settings.LOGGER_NAME)


class TaskWrapper:

    def __init__(self, cls: callable, *args, stop_event:Event=None, started_event:Event=None, stopped_event:Event=None, **kwargs):
        self.stop_event = stop_event or self.new_event()
        self.started_event = started_event or self.new_event()
        self.stopped_event = stopped_event or self.new_event()
        self.instance = cls(*args, **kwargs)
        self.task = self.run()

    def run(self):
        return asyncio.create_task(self.start_task())

    @staticmethod
    def new_event():
        return asyncio.Event()

    async def start_task(self):
        logger.debug('Starting task')
        async with self.instance as c:
            await asyncio.wait([self.stop_event.wait(), c.run(self.started_event)], return_when=asyncio.FIRST_COMPLETED)
        logger.debug('Task stopped')
        self.stopped_event.set()

    async def started(self):
        await self.started_event.wait()

    async def stopped(self):
        await self.stopped_event.wait()

    def cancel(self):
        logger.debug('Cancelling task')
        self.stop_event.set()
