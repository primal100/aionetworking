import asyncio
import datetime

from .base import BaseMessageManager
from lib.utils import log_exception
import settings
import logging


from typing import TYPE_CHECKING, Type
if TYPE_CHECKING:
    from lib.protocols.base import BaseProtocol
else:
    BaseProtocol = None

logger = logging.getLogger(settings.LOGGER_NAME)


class MessageManager(BaseMessageManager):
    name = 'Message Manager'

    async def run(self, started_event):
        started_event.set()
        while True:
            await asyncio.sleep(1)

    async def manage(self, sender, data):
        if self.generate_timestamp:
            timestamp = datetime.datetime.now()
            logger.debug('Generated timestamp: %s', timestamp)
        else:
            timestamp = None
        responses = []
        if self.has_actions_no_decoding:
            msg = self.make_raw_message(sender, data, timestamp=timestamp)
            self.do_raw_actions([msg])
        if self.requires_decoding:
            msgs = self.make_messages(sender, data, timestamp)
            for msg in msgs:
                logger.debug('Managing %s from %s', msg, sender)
                if not msg.filter():
                    tasks = self.do_actions(msg)
                    done, pending = await asyncio.wait(tasks)
                    results = [d.result() for d in done]
                    exceptions = [d.exception() for d in done]
                    for exc in exceptions:
                        if exc:
                            logger.error(log_exception(exc))
                    if self.supports_responses:
                        response = msg.make_response(results, exceptions)
                        if response is not None:
                            responses.append(response)
                else:
                    logger.debug("%s was filtered out" % str(msg).capitalize())
        return responses

    async def cleanup(self):
        logger.debug('Running message manager cleanup')
        for action in self.all_actions:
            await action.close()
        logger.debug('Message manager cleanup completed')

    def _do_actions(self, msg, key='protocol'):
        tasks = [action.do(msg) for action in self.actions[key]['store'].values()]
        tasks += [task for task in [action.print(msg) for action in self.actions[key]['print'].values()] if task]
        logger.debug('Created tasks %s for %s', ','.join([str(id(task)) for task in tasks]), str(msg))
        return tasks

    def do_raw_actions(self, msg):
        logger.debug('Running raw actions')
        return self._do_actions(msg, key='raw')

    def do_actions(self, msg):
        logger.debug('Running actions for %s', msg)
        return self._do_actions(msg, key='protocol')


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
