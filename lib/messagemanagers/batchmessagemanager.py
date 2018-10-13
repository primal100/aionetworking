from .messagemanager import BaseMessageManager


class BatchMessageManager(BaseMessageManager):
    def __init__(self, *args, **kwargs):
        super(BatchMessageManager, self).__init__(*args, **kwargs)
        self.interval = receiver_config.get('interval', 0)
        self.queue = asyncio.Queue()
        self.process_queue_later()

    def process_queue_later(self):
        self.loop.call_later(self.interval, self.process_queue)

    async def decode_run(self, host, encoded, timestamp):
        await self.queue.put((host, encoded, timestamp))

    async def done(self):
        await self.queue.join()

    def do_actions(self, msgs):
        for action in self.actions:
            action.do_multiple(msgs, self.queue)

    async def process_queue(self):
        await self.queue.join()
        msgs = []
        try:
            while not self.queue.empty():
                item = self.queue.get_nowait()
                sender, encoded, timestamp = item
                try:
                    msgs += self.message_cls(sender, encoded, timestamp=timestamp)
                finally:
                    for msg in msgs:
                        self.queue.task_done()
            self.do_actions(msgs)
        finally:
            self.process_queue_later()
