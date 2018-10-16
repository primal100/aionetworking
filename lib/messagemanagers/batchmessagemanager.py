from .messagemanager import BaseMessageManager
import asyncio
import logging

logger = logging.getLogger()


class BatchMessageManager(BaseMessageManager):
    def __init__(self, *args, **kwargs):
        super(BatchMessageManager, self).__init__(*args, **kwargs)
        self.interval = kwargs.get('config', {}).get('interval', 5)
        self.queue = asyncio.Queue()
        self.process_queue_task = asyncio.get_event_loop().create_task(self.process_queue_later())

    async def decode_run(self, host, encoded, timestamp):
        logger.debug('Adding message from %s to asyncio queue' % host)
        await self.queue.put((host, encoded, timestamp))

    def do_actions(self, msgs):
        logger.debug('Handling actions for %s messages in batch' % len(msgs))
        for action in self.actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)

    async def close(self):
        logger.info('Closing Batch Message Manager')
        try:
            timeout = self.interval + 1
            logger.info('Waiting %s seconds for queue to empty' % timeout)
            await asyncio.wait_for(self.queue.join(), timeout=timeout + 1)
            logger.info('Queue empty. Cancelling task')
        except asyncio.TimeoutError:
            logger.error('Queue did not empty. Cancelling task with messages in queue.')
        self.process_queue_task.cancel()
        logger.info('Batch Message Manager closed')

    async def process_queue_later(self):
        await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            await self.process_queue_later()

    async def process_queue(self):
        logger.debug('Processing asyncio queue')
        msgs = []
        try:
            while not self.queue.empty():
                item = self.queue.get_nowait()
                logger.debug('Took item from queue')
                sender, encoded, timestamp = item
                msg = self.make_message(sender, encoded, timestamp)
                if not msg.filter():
                    msgs.append(msg)
                else:
                    logger.debug("Message was filtered out")
            self.do_actions(msgs)
        finally:
            for msg in msgs:
                logger.debug("Setting task done on queue")
                self.queue.task_done()
