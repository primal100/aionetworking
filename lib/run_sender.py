import logging
import settings


import definitions

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.senders.base import BaseSender
else:
    BaseSender = None

logger = logging.getLogger(settings.LOGGER_NAME)


def get_sender() -> BaseSender:

    settings.POSTFIX = 'sender'
    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS)
    settings.CONFIG.configure_logging()

    logger.info('Starting client for %s', settings.APP_NAME)

    receiver_name = settings.CONFIG.receiver

    logger.info('Using client for receiver %s', receiver_name)

    sender_cls = definitions.RECEIVERS[receiver_name]['sender']

    protocol_name = settings.CONFIG.protocol

    logger.info('Using protocol %s', protocol_name)

    protocol = definitions.PROTOCOLS[protocol_name]
    protocol.set_config()

    manager_cls = definitions.CLIENT_MESSAGE_MANAGER

    manager = manager_cls.from_config(protocol)

    sender = sender_cls.from_config(manager)
    return sender
