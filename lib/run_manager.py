import asyncio
import concurrent.futures
import logging

import settings
from lib.wrappers.tasks import TaskWrapper

logger = logging.getLogger(settings.LOGGER_NAME)


def executor_callback(fut):
    if fut.exception():
        logger.error(fut.exception())


def start_manager_as_process(queue):
    print('STARTING')
    import settings
    import definitions
    import logging
    from lib.wrappers.queues import AsyncQueueWrapper
    queue = AsyncQueueWrapper(queue)
    settings.POSTFIX = 'manager'
    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS)
    settings.CONFIG.configure_logging()
    logger = logging.getLogger(settings.LOGGER_NAME)
    logger.info('Starting Message Manager for %s', settings.APP_NAME)
    settings.HOME = settings.CONFIG.home
    settings.DATA_DIR = settings.CONFIG.data_home
    start_manager_as_loop(queue)


def get_protocol_manager():

    import definitions
    protocol_name = settings.CONFIG.protocol

    logger.info('Using protocol %s', protocol_name)
    protocol = definitions.PROTOCOLS[protocol_name]
    protocol.set_config()

    message_manager_is_batch = settings.CONFIG.message_manager_is_batch
    if message_manager_is_batch:
        logger.info('Message manager configured in batch mode')
        manager_cls = definitions.BATCH_MESSAGE_MANAGER
    else:
        manager_cls = definitions.MESSAGE_MANAGER

    return protocol, manager_cls


async def start_manager(queue, **kwargs):
    logger.debug('Starting manager')
    protocol_cls, manager_cls = get_protocol_manager()
    manager_cls.from_config(protocol_cls, queue, **kwargs).process_queue_forever()


def start_manager_task(queue=None):
    return TaskWrapper.get_task(start_manager, queue=queue, run_as=settings.CONFIG.run_as)


def start_manager_as_loop(queue, stop_event, **kwargs):
    logger.debug('Starting manager as loop')
    asyncio.run(start_manager(queue, stop_event, **kwargs))


def start_threaded_manager():
    return ExecutorTaskWrapper.thread(start_manager)


def start_multiprocess_manager():
    return ExecutorTaskWrapper.process(start_manager_as_process)


def start_multiprocess_manager2(queue) -> asyncio.Task:
    executor = concurrent.futures.ThreadPoolExecutor
    return asyncio.create_task(run(executor, start_manager_as_process, queue))



