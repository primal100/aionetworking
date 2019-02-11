import logging

from lib import definitions, settings

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.senders.base import BaseSender
else:
    BaseSender = None

logger = logging.getLogger('sender')


def get_sender(*config_args, configure_logging=False, logger_name='sender', **kwargs) -> BaseSender:

    if config_args:
        cp = definitions.CONFIG_CLS(*config_args, logger_name=logger_name)
    else:
        settings.CONFIG = definitions.CONFIG_CLS(*config_args, logger_name='sender')
        cp = settings.CONFIG

    if configure_logging:
        cp.configure_logging()

    receiver_name = cp.receiver

    logger.info('Getting client for receiver %s', receiver_name)

    sender_cls = definitions.RECEIVERS[receiver_name]['sender']

    protocol_name = cp.protocol

    logger.info('Using protocol %s', protocol_name)

    protocol = definitions.PROTOCOLS[protocol_name]
    protocol.set_config(cp=cp)

    manager_cls = definitions.CLIENT_MESSAGE_MANAGER

    manager = manager_cls.from_config(protocol, cp=cp)

    sender = sender_cls.from_config(manager, cp=cp, **kwargs)
    return sender
