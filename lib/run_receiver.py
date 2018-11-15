import asyncio
import logging
import os

import definitions
import settings
from lib.run_manager import get_protocol_manager
from lib.wrappers.tasks import TaskWrapper


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

    protocol_cls, manager_cls = get_protocol_manager()

    manager_task = TaskWrapper.get_task(manager_cls.from_config, protocol_cls, run_as=settings.CONFIG.run_as)

    queue = manager_task.queue

    receiver_task = TaskWrapper.get_task(receiver_cls.from_config, queue=queue, run_as="asyncio")

    await manager_task.started.wait()
    logger.debug('Manager started')
    await receiver_task.started.wait()
    logger.debug('Receiver started')

    status_change.set()

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        async def wakeup():
            await asyncio.sleep(1)
            await wakeup()
        asyncio.create_task(wakeup())

    try:
        await stop_ordered
        logger.debug('Stop order event set')
    finally:
        receiver_task.cancel_task()
        manager_task.cancel_task()
        await receiver_task.stopped.wait()
        logger.debug('Receiver task stopped')
        await manager_task.stopped.wait()
        logger.debug('Manager task stopped')
        status_change.set()
