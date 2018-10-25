from .base import BaseMessageManager
from lib.protocols.base import BaseProtocol
import definitions

from typing import Sequence
import logging

logger = logging.getLogger(definitions.LOGGER_NAME)


class MessageManager(BaseMessageManager):

    def do_actions(self, msgs: Sequence[BaseProtocol]):
        logger.debug('Handling msg actions for', len(msgs), 'messages without batch')
        for msg in msgs:
            for action in self.store_actions:
                action.do(msg)
            for action in self.print_actions:
                action.print(msg)
        logger.debug('All actions completed')

