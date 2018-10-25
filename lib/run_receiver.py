import logging
import os
import definitions
import asyncio


async def main(status_change=None, stop_ordered=None):

    definitions.CONFIG = definitions.CONFIG_CLS(definitions.APP_NAME, *definitions.CONFIG_ARGS, postfix='receiver')
    definitions.CONFIG.configure_logging()
    definitions.LOGGER_NAME = 'receiver'
    definitions.HOME = definitions.CONFIG.home
    definitions.DATA_DIR = definitions.CONFIG.data_home

    definitions.postfix = 'RECEIVER'
    logger = logging.getLogger(definitions.LOGGER_NAME)

    logger.info('Starting %s' % definitions.APP_NAME)

    receiver_name = definitions.CONFIG.receiver
    logger.info('Using receiver %s' % receiver_name)

    receiver_cls = definitions.RECEIVERS[receiver_name]['receiver']

    protocol_name = definitions.CONFIG.protocol

    logger.info('Using protocol %s' % protocol_name)
    protocol = definitions.PROTOCOLS[protocol_name]
    protocol.set_config()

    message_manager_is_batch = definitions.CONFIG.message_manager_is_batch
    if message_manager_is_batch:
        logger.info('Message manager configured in batch mode')
        manager = definitions.BatchMessageManager.from_config(protocol)
    else:
        manager = definitions.MessageManager.from_config(protocol)

    receiver = receiver_cls(manager, status_change=status_change)

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
