import asyncio
import logging
from pathlib import Path

from lib import settings
from lib.conf import RawStr

class BaseAction:
    name = ''
    key = ''
    configurable = {'timeout': int}

    @classmethod
    def from_config(cls, cp=None, **kwargs):
        cp = cp or settings.CONFIG
        config = cp.section_as_dict(cls.key, **cls.configurable)
        logger = logging.getLogger("%s.actions" % cp.logger_name)
        logger.info('Found configuration for %s:%s', cls.name, config)
        config.update(kwargs)
        config['logger_name'] = cp.logger_name
        return cls(**config)

    def __init__(self, timeout=10, logger_name:str = 'receiver'):
        self.log = logging.getLogger("%s.actions" % logger_name)
        self.timeout = timeout
        self.outstanding_tasks = []

    async def do_many(self, msgs):
        await self.do_many_parallel(msgs)

    async def do_many_parallel(self, msgs):
        self.outstanding_tasks += [asyncio.create_task(self.do_one(msg)) for msg in msgs if not self.filter(msg)]

    async def do_many_sequential(self, msgs):
        for msg in msgs:
            if not self.filter(msg):
                await self.do_one(msg)

    def filter(self, msg):
        return msg.filter()

    def do_one(self, msg):
        raise NotImplementedError

    async def wait_complete(self, **logs_extra):
        if self.outstanding_tasks:
            self.log .debug('Waiting for tasks to complete')
            try:
                await asyncio.wait(self.outstanding_tasks, timeout=self.timeout)
            finally:
                self.outstanding_tasks.clear()

    async def close(self):
        await self.wait_complete()

