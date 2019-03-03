import asyncio


class NamedFutures:
    """Class that allows future results to be named and to be processed in the order they were created"""

    def __init__(self, callback=None):
        self._mapping = dict()
        self._queue = asyncio.Queue()
        self.callback = callback

    def _new(self, name, *args):
        return asyncio.Future()

    def new(self, name, *args):
        fut = self._new(name, *args)
        if self.callback:
            fut.add_done_callback(self.callback)
        self._mapping[name] = fut
        self._queue.put_nowait(name)
        return fut

    def set_result(self, name, *args, **kwargs):
        self._mapping[name].set_result(*args, **kwargs)

    def set_exception(self, name, *args, **kwargs):
        self._mapping[name].set_exception(*args, **kwargs)

    def get(self, name):
        return self._mapping[name]

    async def wait_one(self):
        name, fut = await self.get_next()
        result = await fut
        del self._mapping[name]
        return name, result

    async def wait_take_all(self):
        futs = [await self.get_next()]
        futs += self.get_all()
        futures = [r[1] for r in futs]
        await asyncio.wait(futures)
        for fut in futs:
            del self._mapping[fut[0]]
        return futs

    def get_all(self):
        names = [self._queue.get_nowait() for x in range(0, self._queue.qsize())]
        return [(name, self._mapping[name]) for name in names]

    async def get_next(self):
        name = await self._queue.get()
        return name, self._mapping[name]


class NamedTasks(NamedFutures):
    def _new(self, name, *args):
        coro = args[0]
        return asyncio.create_task(coro)
