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

    def __init__(self, **kwargs):
        pass

    def process(self, msg):
        raise NotImplementedError

    def do_one(self, msg):
        task = asyncio.create_task(self.process(msg))
        self.outstanding_tasks.append(task)

    async def wait_complete(self, **logs_extra):
        if self.outstanding_tasks:
            await asyncio.wait(self.outstanding_tasks)
            self.outstanding_tasks = []

    async def close(self):
        await self.wait_complete()
