import asyncio


class AsyncEventWrapper:
    wrapped = True

    @classmethod
    def multiprocess(cls):
        import multiprocessing
        return cls(multiprocessing.Event())

    @classmethod
    def threaded(cls):
        import threading
        return cls(threading.Event())

    def __init__(self, event):
        self.event = event

    def __getattr__(self, item):
        if item == 'event':
            print(item)
            print(hasattr(self, 'event'))
            pass
        return getattr(self.event, item)

    def wait_sync(self):
        return self.event.wait()

    async def wait(self):
        while not self.event.is_set():
            await asyncio.sleep(0.1)
