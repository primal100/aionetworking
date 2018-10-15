import asyncio
import atexit
import logging
import os
from logging.config import fileConfig


def stop(app_name, loop, manager, receiver):
    logger.info('Stopping %s' % app_name)
    loop.run_until_complete(receiver.close())
    loop.run_until_complete(manager.close())
    loop.close()
    logger.info('%s stopped' % app_name)


def start(app_name, receivers, actions, interfaces, config, log_config_path):

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

    receiver_cls = receivers[config.receiver]
    message_manager_cls = config.message_manager
    interface_cls = interfaces[config.interface]
    loop = asyncio.get_event_loop()
    manager = message_manager_cls(app_name, interface_cls, actions, config, loop=loop)
    receiver = receiver_cls(manager, config, loop=loop)
    atexit.register(stop, app_name, loop, manager, receiver)

    logger.debug('Starting event loop')

    loop.run_forever()
