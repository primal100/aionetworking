from lib.configuration.parser import INIFileConfig
import logging
import os


def get_sender(app_name, receivers, protocols, *config_args, config_cls=INIFileConfig):

    config = config_cls(app_name, *config_args, postfix='sender')
    config.configure_logging()
    logger = logging.getLogger('messageManager')

    sender_cls = receivers[config.receiver]['sender']

    logger.info('Using %s' % sender_cls.sender_type)

    sender = sender_cls.from_config(config.receiver_config, config.client_config, protocols, config.protocol)

    return sender
