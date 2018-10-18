import logging
import os
from lib.configuration.parser import INIFileConfig
import asyncio


async def main(app_name, receivers, actions, protocols, *config_args, config_cls=INIFileConfig,
               started_event=None, stop_event=None, stopped_event=None):

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

    receiver = receiver_cls(manager, config, started_event=started_event, stopped_event=stopped_event)

    if os.name == 'nt':
        """Workaround for windows:
        https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#24775107
        """
        def wakeup():
            if stop_event and stop_event.is_set():
                logger.debug('Stop event set')
                asyncio.create_task(receiver.stop())
            asyncio.get_event_loop().call_later(0.1, wakeup)
        wakeup()

    async with receiver:
        await receiver.run()
