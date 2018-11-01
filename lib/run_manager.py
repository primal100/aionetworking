import asyncio
import concurrent.futures
import logging

import definitions
import settings

logger = logging.getLogger(settings.LOGGER_NAME)


async def run(executor, callback, queue):
    with executor() as pool:
        return await asyncio.get_running_loop().run_in_executor(
            pool, callback, queue)


def start_manager(executor, queue):

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

    callback = manager_cls.from_config(protocol).process_queue_forever

    return asyncio.get_event_loop().create_task(run(executor, callback, queue))


def start_threaded_manager(queue=None):
    from queue import Queue
    queue = queue or Queue()
    executor = concurrent.futures.ThreadPoolExecutor
    return start_manager(executor, queue)


def start_multiprocess_manager(queue=None):
    settings.POSTFIX = 'manager'
    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS)
    settings.CONFIG.configure_logging()
    settings.HOME = settings.CONFIG.home
    settings.DATA_DIR = settings.CONFIG.data_home
    executor = concurrent.futures.ProcessPoolExecutor
    return start_manager(executor, queue)



