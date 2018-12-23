import asyncio
import datetime

from .base import BaseMessageManager
from lib.utils import log_exception
from lib import settings
import logging


from typing import TYPE_CHECKING, Type, AnyStr
if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageManager(BaseMessageManager):
    name = 'Message Manager'

    def do_task_actions(self, msg):
        tasks = []
        for action in self.actions:
            fut = asyncio.ensure_future(action.do_one(msg))
            fut.add_done_callback(self.log_task_exceptions)
            tasks.append(fut)
        return tasks

    async def do_simple_actions(self, msg):
        for action in self.actions:
            try:
                await action.do_one(msg)
            except Exception as exc:
                logger.error(log_exception(exc))

    @staticmethod
    def log_task_exceptions(task):
        exc = task.exception()
        if exc:
            logger.error(log_exception(exc))

    async def wait_simple_actions(self, **logs_extra):
        for action in self.actions:
            await action.wait_complete(**logs_extra)

    async def manage(self, sender, msgs):
        responses = []
        tasks = []
        for msg in msgs:
            if not msg.filter():
                await self.do_simple_actions(msg)
                task_set = self.do_task_actions(msg)
                if self.supports_responses:
                    tasks.append((msg, task_set))
        await self.wait_simple_actions(sender=sender)
        if self.supports_responses:
            for msg, task_set in tasks:
                responses.append(msg.get_response(task_set))
        return responses


class ClientMessageManager(BaseMessageManager):
    name = 'Client Message Manager'

    configurable = {}

    @classmethod
    def from_config(cls, protocol: Type[BaseProtocol], **kwargs):
        config = settings.CONFIG.section_as_dict('MessageManager', **cls.configurable)
        config.update(kwargs)
        return cls(protocol, supports_responses=False, **config)

    async def run(self, started_event):
        started_event.set()

    def __init__(self, *args, **kwargs):
        super(ClientMessageManager, self).__init__(*args, **kwargs)
        self.queue = asyncio.Queue()

    def manage(self, sender, data, timestamp):
        try:
            self.queue.put_nowait((sender, data, timestamp))
        except asyncio.QueueFull:
            asyncio.create_task(self.queue.put(data))

    async def wait_response(self):
        await self.queue.get()
