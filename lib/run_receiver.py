import asyncio
import logging
import os

import definitions
import settings


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

    multiprocess = settings.CONFIG.multiprocess

    if multiprocess:
        from multiprocessing import Queue
        queue = queue or Queue()
        manager_task = definitions.MESSAGE_MANAGER_PROCESS(queue)
    else:
        from queue import Queue
        from lib.run_manager import start_threaded_manager
        queue = queue or Queue
        manager_task = start_threaded_manager(queue)

    receiver = receiver_cls.from_config(queue, status_change=status_change)

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        async def wakeup():
            if stop_ordered and stop_ordered.is_set():
                logger.debug('Stop order event set')
                stop_ordered.clear()
                raise KeyboardInterrupt
            else:
                await asyncio.sleep(1)
                await wakeup()
        asyncio.create_task(wakeup())

    async with receiver:
        await receiver.run()
    manager_task.cancel()
