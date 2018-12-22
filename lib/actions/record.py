import asyncio
import logging
from pathlib import Path

from .base import BaseAction
from lib import utils, settings

from typing import Sequence
from datetime import datetime, timedelta

logger = logging.getLogger(settings.LOGGER_NAME)


class Action(BaseAction):
    requires_decoding = False
    store_many_write_mode = 'ab'
    prev_message_time = 0

    def get_content(self, msg: Sequence[str, bytes, timedelta]):
        return utils.pack_recorded_packet(*msg)

    def store_many(self, msgs: Sequence[Sequence[str, bytes, datetime]]):
        data = b''
        for sender, msg, timestamp in msgs:
            logger.debug('Recording packet from %s', sender)
            timestamp = timestamp or datetime.now()
            if self.prev_message_time:
                message_timedelta = (timestamp - self.prev_message_time).microseconds
            else:
                message_timedelta = 0
            self.prev_message_time = timestamp
            data += self.get_content((sender, msg, message_timedelta))
        record_file_path = Path('')
        record_file_path.parent.mkdir(exist_ok=True, parents=True)
        asyncio.create_task(self.write_to_file(record_file_path, data, 'ab'))

    def do(self, msg: Sequence[str, bytes, datetime]):
        self.store_many([msg])
