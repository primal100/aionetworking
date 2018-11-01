from .base import BaseMessageManager
import settings
import logging

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageManager(BaseMessageManager):
    queue = None
    store_actions = ()
    print_actions = ()

    def make_message(self, sender, encoded, timestamp):
        raise NotImplementedError

    def process_queue(self):
        while not self.queue.empty():
            item = self.queue.get()
            try:
                logger.debug('Took item from queue')
                sender, encoded, timestamp = item
                msg = self.make_message(sender, encoded, timestamp)
                if not msg.filter():
                    self.do_actions([msg])
                else:
                    logger.debug("Message was filtered out")
            finally:
                logger.debug("Setting task done on queue")
                self.queue.task_done()

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages without batch', len(msgs))
        for msg in msgs:
            for action in self.store_actions:
                action.do(msg)
            for action in self.print_actions:
                action.print(msg)
        logger.debug('All actions completed')


class BatchMessageManager(BaseMessageManager):

    def make_message(self, sender, encoded, timestamp):
        raise NotImplementedError

    def process_queue(self):
        msgs = []
        while not self.queue.empty():
            try:
                item = self.queue.get()
                try:
                    logger.debug('Took item from queue')
                    sender, encoded, timestamp = item
                    msg = self.make_message(sender, encoded, timestamp)
                    if not msg.filter():
                        msgs.append(msg)
                    else:
                        logger.debug("Message was filtered out")
                finally:
                    logger.debug("Setting task done on queue")
                    self.queue.task_done()
            finally:
                self.do_actions(msgs)

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages in batch mode', len(msgs))
        for action in self.store_actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)
        logger.debug('All actions completed')
