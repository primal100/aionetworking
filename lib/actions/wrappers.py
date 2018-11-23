import asyncio
import logging

import settings


logger = logging.getLogger(settings.LOGGER_NAME)


class QueueWrapper:
    def __init__(self, action, interval=1):
        self.action = action
        self.interval = interval
        self.queue = asyncio.Queue()
        self.task = asyncio.create_task(self.process_queue_forever())

    def __getattr__(self, item):
        return getattr(self.action, item)

    async def process_queue_forever(self):
        await asyncio.sleep(self.interval)
        await self.process_queue()
        await self.process_queue_forever()

    async def process_queue(self):
        items = []
        while not self.queue.empty():
            items.append(self.queue.get_nowait())
        await self.process_items(items)

    async def process_items(self, items):
        await self.action.do_multiple(items)
        for i in range(0, len(items)):
            self.queue.task_done()

    async def do(self, msg):
        data = await self.action.prepare_for_multi(msg)
        if data is not None:
            await self.queue.put(data)

    def close(self):
        timeout = self.interval + 1
        try:
            logger.debug('Waiting for queue to be processed for %s action', self.action.action_name)
            asyncio.wait_for(self.queue.join(), timeout=timeout)
            logger.debug('Queue is empty for %s action', self.action.action_name)
        except asyncio.TimeoutError:
            logger.error('Queue not empty when closing %s action', self.action.action_name)
        self.task.cancel()
