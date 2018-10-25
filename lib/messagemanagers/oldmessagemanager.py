from .base import BaseMessageManager

import definitions
import logging

logger = logging.getLogger(definitions.LOGGER_NAME)


class MessageManager(BaseMessageManager):

    async def close(self):
        logger.info('Message Manager closed')

    def do_actions(self, msg):
        logger.debug('Handling msg actions without batch')
        for action in self.store_actions:
            action.do(msg)
        for action in self.print_actions:
            action.print(msg)
        logger.debug('All actions completed')

    async def decode_run(self, sender, encoded, timestamp):
        msg = self.make_message(sender, encoded, timestamp)
        if not msg.filter():
            self.do_actions(msg)
        else:
            logger.debug("Message was filtered out")

