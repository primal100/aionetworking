import asyncio
import logging
import os
import sys

from lib import definitions, settings
from lib.run_manager import get_protocol_manager
from lib.utils import log_exception
from lib.wrappers.events import AsyncEventWrapper


def except_handler(logger, exc_type, exc_value, exc_tb):
    logger.exception('', exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


# Install exception handler
#sys.excepthook = except_handler


logger = logging.getLogger('receiver')


def log_exceptions(logger, loop, context):
    logger.error(context['message'])
    logger.error(log_exception(context['exception']))
    loop.default_exception_handler(context)


async def main(*config_args, status_change=None, stop_ordered=None, logger_name='receiver', configure_logging=True):

    config_args = config_args or settings.CONFIG_ARGS
    cp = definitions.CONFIG_CLS(*config_args, logger_name=logger_name)

    if configure_logging:
        cp.configure_logging()

    logger = logging.getLogger(logger_name)

    loop = asyncio.get_event_loop()

    #exception_handler = partial(log_exception, logger)
    loop.set_exception_handler(log_exceptions)
    logger.info('Starting %s on %s', settings.APP_NAME, asyncio.get_event_loop())

    receiver_name = cp.receiver
    logger.info('Using receiver %s', receiver_name)

    receiver_cls = definitions.RECEIVERS[receiver_name]['receiver']

    protocol_cls, manager_cls = get_protocol_manager(cp=cp)

    manager = manager_cls.from_config(protocol_cls, cp=cp)

    receiver = receiver_cls.from_config(manager, cp=cp)
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
        await asyncio.sleep(0.1)
        if status_change:
            status_change.set()
