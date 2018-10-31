import logging
import settings
settings.LOGGER_NAME = 'sender'

import definitions

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.senders.base import BaseSender
else:
    BaseSender = None


def get_sender() -> BaseSender:

    settings.CONFIG = definitions.CONFIG_CLS(*settings.CONFIG_ARGS, postfix='sender')
    settings.CONFIG.configure_logging()
    settings.postfix = 'sender'

    logger = logging.getLogger(settings.LOGGER_NAME)
    logger.info('Starting client for %s', settings.APP_NAME)

    receiver_name = settings.CONFIG.receiver

    logger.info('Using client for receiver %s', receiver_name)

    sender_cls = definitions.RECEIVERS[receiver_name]['sender']

    protocol_name = settings.CONFIG.protocol

    logger.info('Using protocol %s', protocol_name)

    protocol = definitions.PROTOCOLS[protocol_name]
    protocol.set_config()

    sender = sender_cls.from_config(protocol)
    return sender
