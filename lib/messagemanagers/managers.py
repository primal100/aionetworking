from .base import BaseMessageManager
import settings
import logging
import asyncio

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageManager(BaseMessageManager):
    name = 'Message Manager'

    async def process_queue(self):
        logger.debug('Getting item from queue')
        item = await self.queue.get()
        tasks = []
        try:
            logger.debug('Took item from queue')
            sender, encoded, timestamp = item
            if self.has_actions_no_decoding:
                tasks = tasks + self.do_raw_actions([(item, sender)])
            if self.requires_decoding:
                msgs = self.make_messages(sender, encoded, timestamp)
                for msg in msgs:
                    if not msg.filter():
                        tasks = tasks + self.do_actions([(msg, sender)])
                    else:
                        logger.debug("Message was filtered out")
        finally:
            asyncio.create_task(self.task_done(tasks))

    def do_raw_actions(self, msgs):
        logger.debug('Running raw actions')
        tasks = []
        for msg, sender in msgs:
            for action in self.store_actions:
                if not action.requires_decoding:
                    task = action.do(msg, sender)
                    if task:
                        tasks.append(task)
            for action in self.print_actions:
                if not action.requires_decoding:
                    task = action.print(msg, sender)
                    if task:
                        task.append(task)
        return tasks

    def do_actions(self, msgs):
        logger.debug('Running actions')
        tasks = []
        for msg, sender in msgs:
            for action in self.store_actions:
                if action.requires_decoding:
                    task = action.do(msg, sender)
                    if task:
                        tasks.append(task)
            for action in self.print_actions:
                if action.requires_decoding:
                    task = action.print(msg, sender)
                    if task:
                        tasks.append(task)
        return tasks



class BatchMessageManager(BaseMessageManager):
    name = 'Batch Message Manager'

    def process_queue(self):
        decoded_msgs = []
        raw_msgs = []
        num_items = 0
        while not self.queue.empty():
            item = self.queue.get()
            num_items += 1
            try:
                logger.debug('Took item from queue')
                if self.record:
                    raw_msgs.append(item)
                if self.has_actions:
                    sender, encoded, timestamp = item
                    msgs = self.make_messages(sender, encoded, timestamp)
                    for msg in msgs:
                        if not msg.filter():
                            decoded_msgs.append(msg)
                    else:
                        logger.debug("Message was filtered out")
            except Exception as e:
                logger.error(e)
        try:
            if raw_msgs:
                self.record_packets(raw_msgs)
        finally:
            try:
                if decoded_msgs:
                    self.do_actions(decoded_msgs)
            finally:
                    self.task_done(num_times=num_items)

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages in batch mode', len(msgs))
        for action in self.store_actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)
        logger.debug('All actions completed')
