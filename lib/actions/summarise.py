from .decode import Action as BaseStoreAction
import os
from lib import utils


class Action(BaseStoreAction):
    """
    To store or display summaries of all data received each day
    """
    action_name = 'Summarise'
    default_data_dir = "Summaries"
    single_extension = "csv"
    multi_extension = "csv"
    store_write_mode = 'a+'

    def get_content(self, msg):
        return msg.summaries

    def get_content_multi(self, msg):
        return self.get_content(msg)

    def print(self, msg):
        print(self.print_msg(msg))

    def print_msg(self, msg):
        content = self.get_content(msg)
        return '\n'.join(['\t'.join([str(cell) for cell in row]) for row in content])

    @property
    def path(self):
        return os.path.join(self.base_path, "Summary_%s.%s" % (utils.current_date(), self.single_extension))

    def do(self, msg):
        utils.append_to_csv(self.path, self.get_content(msg))

    def store_many(self, msgs):
        lines = sum([self.get_content(msg) for msg in msgs], [])
        utils.append_to_csv(self.path, lines)
