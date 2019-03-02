import asyncio


class Counter:

    def __init__(self):
        self.event = asyncio.Event()
        self._value = 0

    def increment(self, num=1):
        if self._value == 0:
            self.event.clear()
        self._value += num

    def decrease(self, num=1):
        self._value -= num
        if self._value == 0:
            self.event.set()

    def all_done(self):
        return self._value == 0

    async def wait(self):
        await self.event.wait()


class TaskCounter(Counter):

    def task_done(self, task):
        self.decrease()

    def create_task(self, coro):
        task = asyncio.create_task(coro)
        self.increment()
        task.add_done_callback(self.task_done)
        return task
