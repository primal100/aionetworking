import asyncio
import logging
import os

from lib import definitions, settings
from lib.run_manager import get_protocol_manager
from lib.utils import log_exception
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

    loop = asyncio.get_event_loop()

    #loop.set_exception_handler(log_exceptions)
    logger.info('Starting %s on %s', settings.APP_NAME, asyncio.get_event_loop())

    receiver_name = settings.CONFIG.receiver
    logger.info('Using receiver %s', receiver_name)

    receiver_cls = definitions.RECEIVERS[receiver_name]['receiver']

    protocol_cls, manager_cls = get_protocol_manager()

    manager = manager_cls.from_config(protocol_cls)

    receiver = receiver_cls.from_config(manager)
    receiver_task = asyncio.create_task(receiver.start())

    await receiver.started()
    logger.debug('Receiver started')

    if status_change:
        status_change.set()

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        def wakeup():
            loop.call_later(0.1, wakeup)
        loop.call_later(0.1, wakeup)

    try:
        if stop_ordered:
            if not isinstance(stop_ordered, asyncio.Event):
                stop_ordered = AsyncEventWrapper(stop_ordered)
            await stop_ordered.wait()
        else:
            await receiver_task
    finally:
        receiver_task.cancel()
        await receiver.stopped()
        logger.debug('Receiver task stopped')
        await manager.close()
        logger.debug('Message Manager closed')
        if status_change:
            status_change.set()
