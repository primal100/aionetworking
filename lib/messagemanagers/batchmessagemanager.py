from .messagemanager import BaseMessageManager
import logging

logger = logging.getLogger('messageManager')


class BatchMessageManager(BaseMessageManager):
    batch = True

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages in batch mode' % len(msgs))
        for action in self.store_actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)
        logger.debug('All actions completed')
