from .base import BaseMessageManager
import asyncio
import settings
import logging

from typing import AnyStr
from datetime import datetime

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseAsyncioMessageManager(BaseMessageManager):

    def __init__(self, protocol,  *args, queue=None, **kwargs):
        queue = queue or asyncio.Queue()
        super(BaseAsyncioMessageManager, self).__init__(protocol, queue, *args, **kwargs)
        self.process_queue_task = asyncio.get_event_loop().create_task(self.process_queue_forever())

    async def close(self):
        logger.info('Closing Asyncio Message Manager')
        try:
            timeout = self.interval + 1
            logger.info('Waiting %s seconds for queue to empty', timeout)
            await asyncio.wait_for(self.queue.join(), timeout=timeout + 1)
            logger.info('Queue empty. Cancelling task')
        except asyncio.TimeoutError:
            logger.error('Queue did not empty. Cancelling task with messages in queue.')
        self.process_queue_task.cancel()
        logger.info('Batch Message Manager closed')

    async def add_to_queue(self, host: str, encoded: AnyStr, timestamp: datetime):
        await self.queue.put((host, encoded, timestamp))
