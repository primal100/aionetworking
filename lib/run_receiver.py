import asyncio
import logging
import os

import definitions
import settings


async def main(status_change=None, stop_ordered=None):

    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS, postfix='receiver')
    settings.CONFIG.configure_logging()
    settings.LOGGER_NAME = 'receiver'
    settings.HOME = settings.CONFIG.home
    settings.DATA_DIR = settings.CONFIG.data_home

    settings.postfix = 'RECEIVER'
    logger = logging.getLogger(settings.LOGGER_NAME)

    logger.info('Starting %s', settings.APP_NAME)

    receiver_name = settings.CONFIG.receiver
    logger.info('Using receiver %s', receiver_name)

    receiver_cls = definitions.RECEIVERS[receiver_name]['receiver']

    protocol_name = settings.CONFIG.protocol

    logger.info('Using protocol %s', protocol_name)
    protocol = definitions.PROTOCOLS[protocol_name]
    protocol.set_config()

    message_manager_is_batch = settings.CONFIG.message_manager_is_batch
    if message_manager_is_batch:
        logger.info('Message manager configured in batch mode')
        manager_cls = definitions.BatchMessageManager
    else:
        manager_cls = definitions.MessageManager

    manager = manager_cls.from_config(protocol)
    receiver = receiver_cls.from_config(manager, status_change=status_change)

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        def wakeup():
            if stop_ordered and stop_ordered.is_set():
                logger.debug('Stop order event set')
                asyncio.create_task(receiver.stop())
            asyncio.get_event_loop().call_later(0.1, wakeup)
        wakeup()

    async with receiver:
        await receiver.run()
