from .messagemanager import BaseMessageManager
import asyncio


class BatchMessageManager(BaseMessageManager):
    def __init__(self, *args, **kwargs):
        super(BatchMessageManager, self).__init__(*args, **kwargs)
        self.interval = kwargs.get('config', {}).get('interval', 5)
        self.queue = asyncio.Queue()
        self.process_queue_task = self.loop.create_task(self.process_queue_later())

    async def decode_run(self, host, encoded, timestamp):
        await self.queue.put((host, encoded, timestamp))

    async def done(self):
        await self.queue.join()

    def do_actions(self, msgs):
        for action in self.actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)

    def close(self):
        self.process_queue_task.cancel()

    async def process_queue_later(self):
        await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            await self.process_queue_later()

    async def process_queue(self):
        msgs = []
        try:
            while not self.queue.empty():
                print(self.queue.qsize())
                item = self.queue.get_nowait()
                sender, encoded, timestamp = item
                msgs.append(self.message_cls(sender, encoded, timestamp=timestamp))
            self.do_actions(msgs)
        finally:
            for msg in msgs:
                self.queue.task_done()
