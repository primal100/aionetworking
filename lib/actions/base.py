import asyncio

from lib import settings

logger = settings.get_logger('actions')


class BaseAction:
    name = ''
    key = ''
    outstanding_tasks = []
    configurable = {}

    @classmethod
    def from_config(cls, cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict(cls.key, **cls.configurable)
        logger.debug('Found configuration for %s:%s', cls.name, config)
        config.update(kwargs)
        return cls(**config)

    def __init__(self, **kwargs): ...

    async def do_many(self, msgs):
        await self.do_many_parallel(msgs)

    async def do_many_parallel(self, msgs):
        self.outstanding_tasks += [asyncio.create_task(self.do_one(msg)) for msg in msgs]

    async def do_many_sequential(self, msgs):
        for msg in msgs:
            await self.do_one(msg)

    def do_one(self, msg):
        raise NotImplementedError

    async def wait_complete(self, **logs_extra):
        if self.outstanding_tasks:
            try:
                await asyncio.wait(self.outstanding_tasks)
            finally:
                self.outstanding_tasks = []

    async def close(self):
        await self.wait_complete()
