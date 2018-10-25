from .messagemanager import BaseMessageManager
from lib.protocols.base import BaseProtocol
import definitions

from typing import Sequence

import logging

logger = logging.getLogger(definitions.LOGGER_NAME)


class BatchMessageManager(BaseMessageManager):
    batch = True

    def do_actions(self, msgs:Sequence[BaseProtocol]):
        logger.debug('Handling msg actions for', len(msgs), 'messages in batch mode')
        for action in self.store_actions:
            action.do_multiple(msgs)
        for action in self.print_actions:
            for msg in msgs:
                action.print(msg)
        logger.debug('All actions completed')
