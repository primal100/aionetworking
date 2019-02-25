import logging

from lib import definitions, settings

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lib.senders.base import BaseSender
else:
    BaseSender = None


def get_sender(*config_args, configure_logging=False, logger_name='sender', **kwargs) -> BaseSender:

    config_args = config_args or settings.CONFIG_ARGS
    cp = definitions.CONFIG_CLS(*config_args, logger_name=logger_name)

    if configure_logging:
        cp.configure_logging()

    logger = logging.getLogger(logger_name)

    receiver_name = cp.receiver

    logger.info('Getting client for receiver %s', receiver_name)

    sender_cls = definitions.RECEIVERS[receiver_name]['sender']

    protocol_name = cp.protocol

    logger.info('Using protocol %s', protocol_name)

    protocol = definitions.PROTOCOLS[protocol_name]

    manager_cls = definitions.CLIENT_MESSAGE_MANAGER

    manager = manager_cls.from_config(protocol, cp=cp)

    sender = sender_cls.from_config(manager, cp=cp, **kwargs)
    return sender
