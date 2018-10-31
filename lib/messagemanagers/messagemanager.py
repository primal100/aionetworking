from .asynciomessagemanager import BaseAsyncioMessageManager
import settings
import logging

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageManager(BaseAsyncioMessageManager):
    name = 'Asyncio Message Manager'

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages without batch', len(msgs))
        for msg in msgs:
            for action in self.store_actions:
                action.do(msg)
            for action in self.print_actions:
                action.print(msg)
        logger.debug('All actions completed')

