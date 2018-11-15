import asyncio
import logging
import csv
from io import StringIO

import settings
from .decode import Action as BaseStoreAction
from lib.utils import current_date

from pathlib import Path
from typing import Sequence

logger = logging.getLogger(settings.LOGGER_NAME)


class Action(BaseStoreAction):
    """
    To store or display summaries of all data received each day
    """
    action_name = 'Summarise'
    default_data_dir = "Summaries"
    single_extension = "csv"
    multi_extension = "csv"
    store_write_mode = 'a'

    def get_content(self, msg) -> str:
        s = StringIO()
        writer = csv.writer(s, delimiter='\t', lineterminator='\n')
        writer.writerows(msg.summaries)
        return s.getvalue()

    def print(self, msg):
        if not self.filtered(msg, True):
            print(self.print_msg(msg))
        else:
            logger.debug("Message filtered for action %s", self.action_name)

    def print_msg(self, msg):
        content = self.get_content(msg)
        return content.rstrip("\n\r")

    def get_storage_filename_single(self, msg):
        return "Summary_%s.%s" % (current_date(), self.single_extension)

    def get_storage_path_single(self, msg) -> Path:
        return self.base_path.joinpath("Summary_%s.%s" % (current_date(), self.single_extension))

    def store_many(self, msgs):
        logger.debug('Storing %s messages for action', len(msgs), self.action_name)
        lines = sum([self.get_content(msg) for msg in msgs], [])
        asyncio.create_task(self.append_to_csv(self.path, lines))
