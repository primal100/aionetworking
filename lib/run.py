import asyncio
import logging
import os
from logging.config import fileConfig


async def main(app_name, receivers, actions, protocols, config, log_config_path):

    logging_setup = False
    while not logging_setup:
        try:
            fileConfig(log_config_path)
            logging_setup = True
        except FileNotFoundError as e:
            log_directory = os.path.dirname(e.filename)
            os.makedirs(log_directory, exist_ok=True)

    logger = logging.getLogger()
    logger.info('Starting %s' % app_name)
    logger.debug('Using logging config file %s' % log_config_path)

    receiver_cls = receivers[config.receiver]['receiver']
    message_manager_cls = config.message_manager
    protocol = protocols[config.protocol]
    manager = message_manager_cls(app_name, protocol, actions, config)
    receiver = receiver_cls(manager, config)

    if os.name == 'nt':
        #Following two lines can be removed in Python 3.8 as ProactorEventLoop will be default for windows.
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        def wakeup():
            asyncio.get_event_loop().call_later(0.1, wakeup)
        wakeup()

    logger.debug('Starting event loop')

    async with receiver:
        await receiver.run()
