import asyncio

from .base import BaseMessageManager
import settings
import logging

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageManager(BaseMessageManager):
    name = 'Message Manager'

    async def run(self, started_event):
        started_event.set()

    async def manage_with_no_response(self, sender, data, timestamp):
        todo = []
        if self.has_actions_no_decoding:
            msg = self.make_raw_message(sender, data, timestamp=timestamp)
            for action_name, info in self.do_raw_store_actions([msg]):
                todo.append({'action': self.store_actions[action_name], 'args': info})
            for action_name, info in self.do_raw_print_actions([msg]):
                todo.append({'action': self.store_actions[action_name], 'args': info})
        if self.requires_decoding:
            msgs = self.make_messages(sender, data, timestamp)
            for msg in msgs:
                if not msg.filter():
                    for action_name, info in self.do_store_actions([msg]):
                        todo.append({'action': self.store_actions[action_name], 'args': info})
                    for action_name, info in self.do_print_actions([msg]):
                        todo.append({'action': self.print_actions[action_name], 'args': info})
                else:
                    logger.debug("Message was filtered out")
        return todo

    async def manage_in_executor(self, *args):
        todo = await self.executor(self.manage_with_no_response, *args)
        for do in todo:
            action = do['action']
            args = do['args']
            await action.execute(*args)

    async def manage(self, sender, data, timestamp):
        logger.debug('Received msg from %s' % sender)
        responses = []
        if self.has_actions_no_decoding:
            msg = self.make_raw_message(sender, data, timestamp=timestamp)
            self.do_raw_actions([msg])
        if self.requires_decoding:
            msgs = self.make_messages(sender, data, timestamp)
            for msg in msgs:
                if not msg.filter():
                    tasks = self.do_actions([(msg, sender)])
                    response = msg.make_response(tasks)
                    if response is not None:
                        responses.append(response)
                else:
                    logger.debug("Message was filtered out")
        return responses

    @staticmethod
    def gather_actions(self, msg):
        logger.debug('Running actions')
        store_actions = [action for action in self.store_actions if action.requires_decoding]
        print_actions = [action for action in self.print_actions if action.requires_decoding]
        return self._gather_actions(msg, store_actions, print_actions)

    @staticmethod
    def _gather_actions(msg, store_actions, print_actions):
        store_info = {action.action_name: action.store_info(msg) for action in store_actions}
        print_info = {action.action_name: action.print_msg(msg) for action in print_actions}
        return store_info, print_info

    @staticmethod
    def _do_actions(msg, store_actions, print_actions):
        tasks = [task for task in [(action.action_name, action.do(msg)) for action in store_actions] if task[1]]
        tasks += [task for task in [(action.action_name, action.do(msg)) for action in print_actions] if task]
        return tasks

    def do_raw_actions(self, msg):
        logger.debug('Running raw actions')
        store_actions = [action for action in self.store_actions if not action.requires_decoding]
        print_actions = [action for action in self.print_actions if not action.requires_decoding]
        return self._do_actions(msg, store_actions, print_actions)

    def do_actions(self, msg):
        logger.debug('Running actions')
        store_actions = [action for action in self.store_actions if action.requires_decoding]
        print_actions = [action for action in self.print_actions if action.requires_decoding]
        return self._do_actions(msg, store_actions, print_actions)


class BatchMessageManager(BaseMessageManager):
    name = 'Batch Message Manager'
    configurable = BaseMessageManager.configurable.copy()
    configurable.update({'interval': float})

    def __init__(self, *args, interval: float=1, **kwargs):
        super(BatchMessageManager, self).__init__(*args, **kwargs)
        self.interval = interval
        self.queue = asyncio.Queue()
        self.task = asyncio.create_task(self.process_queue_forever())

    async def manage(self, sender, data, timestamp):
        logger.debug('Received msg from %s. Adding to queue.' % sender)
        await self.queue.put((sender, data, timestamp))

    async def process_queue_forever(self):
        await asyncio.sleep(self.interval)
        await self.process_queue()
        await self.process_queue_forever()

    async def run(self, started_event):
        logger.debug('Starting queue-based message manager')
        started_event.set()
        await self.process_queue_forever()

    def process_queue(self):
        msgs = []
        raw_msgs = []
        num_items = 0
        while not self.queue.empty():
            item = self.queue.get_nowait()
            num_items += 1
            try:
                logger.debug('Took item from queue')
                if self.has_actions_no_decoding:
                    msg = self.make_raw_message(*item)
                    raw_msgs += msg
                if self.requires_decoding:
                    _msgs = self.make_messages(*item)
                    for msg in _msgs:
                        if not msg.filter():
                            msgs.append(msg)
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
                    for i in range(0, num_items):
                        logger.debug('Setting task done on queue')
                        self.queue.task_done()

    def do_actions(self, msgs):
        logger.debug('Handling msg actions for %s messages in batch mode', len(msgs))
        for action in self.store_actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)
        logger.debug('All actions completed')

    async def cleanup(self):
        timeout = 10
        logger.info('Waiting %s seconds for queue to empty', timeout)
        #await self.queue.join()
        try:
            join_result = await asyncio.wait_for(self.queue.join(), timeout)
            logger.info('Queue empty')
        except asyncio.TimeoutError:
            logger.error('Queue did not empty')
        logging.info('%s application stopped', self.receiver_type)
        self.set_status_changed('stopped')