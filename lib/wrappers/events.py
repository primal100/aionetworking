import asyncio


class AsyncEventWrapper:
    wrapped = True

    def __init__(self, event):
        self.event = event

    def __getattr__(self, item):
        return getattr(self.event, item)

    async def wait(self):
        return await asyncio.get_running_loop().run_in_executor(None, self.event.wait())
