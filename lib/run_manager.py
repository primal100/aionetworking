import logging

from lib import settings

logger = logging.getLogger(settings.LOGGER_NAME)


def get_protocol_manager(cp=settings.CONFIG):

    from lib import definitions
    protocol_name = cp.protocol

    logger.info('Using protocol %s', protocol_name)
    protocol = definitions.PROTOCOLS[protocol_name]

    manager_cls = definitions.MESSAGE_MANAGER

    return protocol, manager_cls
