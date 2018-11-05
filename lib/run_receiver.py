import asyncio
import logging
import os

import definitions
import settings
from lib.wrappers.queues import AsyncQueueWrapper
from lib.conf import ConfigurationException


logger = logging.getLogger(settings.LOGGER_NAME)


async def main(queue=None, status_change=None, stop_ordered=None):

    settings.POSTFIX = 'receiver'
    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS)
    settings.CONFIG.configure_logging()
    settings.HOME = settings.CONFIG.home
    settings.DATA_DIR = settings.CONFIG.data_home

    logger.info('Starting %s', settings.APP_NAME)

    receiver_name = settings.CONFIG.receiver
    logger.info('Using receiver %s', receiver_name)

    receiver_cls = definitions.RECEIVERS[receiver_name]['receiver']

    run_as = settings.CONFIG.run_as

    if run_as == 'process':
        logger.info('Multiprocessing enabled for message manager')
        from lib.run_manager_multiprocess import start_multiprocess_manager, queue
        manager_task = start_multiprocess_manager()
    elif run_as == 'thread':
        logger.info('Threading enabled for message manager')
        from queue import Queue
        from lib.run_manager import start_threaded_manager
        queue = queue or AsyncQueueWrapper(Queue())
        manager_task = start_threaded_manager(queue)
    elif run_as == 'asyncio' or not run_as:
        logger.info('Asyncio enabled for message manager')
        from lib.run_manager import start_manager
        queue = queue or asyncio.Queue()
        manager_task = asyncio.create_task(start_manager(queue))
    else:
        raise ConfigurationException('%s not supported for run_as paramater. Choose one of asyncio, thread or process' % run_as)

    receiver = receiver_cls.from_config(queue, status_change=status_change)

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        async def wakeup():
            if stop_ordered and stop_ordered.is_set():
                logger.debug('Stop order event set')
                stop_ordered.clear()
                await receiver.stop()
            else:
                await asyncio.sleep(1)
                await wakeup()
        asyncio.create_task(wakeup())

    async with receiver:
        await receiver.run()
    manager_task.cancel()
