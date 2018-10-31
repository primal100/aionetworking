from .asynciomessagemanager import BaseAsyncioMessageManager
import settings
import logging
import asyncio

logger = logging.getLogger(settings.LOGGER_NAME)


class BatchMessageManager(BaseAsyncioMessageManager):
    batch = True
    name = "Asyncio Batch Message Manager"

    async def process_queue_forever(self):
        if self.interval:
            await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            logger.debug('processing queue later')
            await self.process_queue_forever()

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages in batch mode', len(msgs))
        for action in self.store_actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)
        logger.debug('All actions completed')
