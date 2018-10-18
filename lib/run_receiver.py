import logging
import os
from lib.configuration.parser import INIFileConfig


async def main(app_name, receivers, actions, protocols, *config_args, config_cls=INIFileConfig):

    config = config_cls(app_name, *config_args, postfix='receiver')
    config.configure_logging()
    logger = logging.getLogger('messageManager')

    receiver_cls = receivers[config.receiver]['receiver']

    logger.info('Starting %s' % app_name)
    logger.info('Using receiver %s' % config.receiver)

    logger.info('Using protocol %s' % config.protocol)
    protocol = protocols[config.protocol]

    message_manager_cls = config.message_manager
    manager = message_manager_cls(app_name, protocol, actions, config)

    if manager.batch:
        logger.info('Message manager configured in batch mode')

    receiver = receiver_cls(manager, config)

    if os.name == 'nt':
        import asyncio
        # Following two lines can be removed in Python 3.8 as ProactorEventLoop will be default for windows.
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        def wakeup():
            asyncio.get_event_loop().call_later(0.1, wakeup)
        wakeup()

    async with receiver:
        await receiver.run()
