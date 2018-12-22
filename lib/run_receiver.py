import asyncio
import logging
import os

from lib import definitions, settings
from lib.run_manager import get_protocol_manager
from lib.utils import log_exception
from lib.wrappers.tasks import TaskWrapper
from lib.wrappers.events import AsyncEventWrapper


logger = logging.getLogger(settings.LOGGER_NAME)


def log_exceptions(loop, context):
    logger.error(context['message'])
    logger.error(log_exception(context['exception']))
    raise context['exception']


async def main(status_change=None, stop_ordered=None):

    settings.POSTFIX = 'receiver'
    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS)
    settings.CONFIG.configure_logging()
    settings.HOME = settings.CONFIG.home
    settings.DATA_DIR = settings.CONFIG.data_home

    asyncio.get_event_loop().set_exception_handler(log_exceptions)
    logger.info('Starting %s on %s', settings.APP_NAME, asyncio.get_event_loop())

    receiver_name = settings.CONFIG.receiver
    logger.info('Using receiver %s', receiver_name)

    receiver_cls = definitions.RECEIVERS[receiver_name]['receiver']

    protocol_cls, manager_cls = get_protocol_manager()

    manager_task = TaskWrapper(manager_cls.from_config, protocol_cls)

    receiver_task = TaskWrapper(receiver_cls.from_config, manager_task.instance)

    await manager_task.started()
    logger.debug('Manager started')

    await receiver_task.started()
    logger.debug('Receiver started')

    if status_change:
        status_change.set()

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        async def wakeup():
            await asyncio.sleep(0.1)
            await wakeup()
        asyncio.create_task(wakeup())

    if not isinstance(stop_ordered, asyncio.Event):
        stop_ordered = AsyncEventWrapper(stop_ordered)

    try:
        if stop_ordered:
            await stop_ordered.wait()
            logger.debug('Stop order event set')
        else:
            while True:
                pass
    finally:
        receiver_task.cancel()
        await receiver_task.stopped()
        logger.debug('Receiver task stopped')
        manager_task.cancel()
        await manager_task.stopped()
        logger.debug('Manager task stopped')
        status_change.set()
