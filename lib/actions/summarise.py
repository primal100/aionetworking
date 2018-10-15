from .decode import Action as BaseStoreAction
import os
from lib import utils
import logging

logger = logging.getLogger()


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
        if not msg.filter_by_action(self, True):
            print(self.print_msg(msg))
        else:
            logger.debug("Message filtered for action %s" % self.action_name)

    def print_msg(self, msg):
        content = self.get_content(msg)
        return '\n'.join(['\t'.join([str(cell) for cell in row]) for row in content])

    @property
    def path(self):
        path = os.path.join(self.base_path, "Summary_%s.%s" % (utils.current_date(), self.single_extension))
        logger.debug('Using path %s' % path)
        return path

    def do(self, msg):
        if not msg.filter_by_action(self, False):
            utils.append_to_csv(self.path, self.get_content(msg))
        else:
            logger.debug("Message filtered for action %s" % self.action_name)

    def store_many(self, msgs):
        logger.debug('Storing %s messages for action %s' % (len(msgs), self.action_name))
        lines = sum([self.get_content(msg) for msg in msgs], [])
        utils.append_to_csv(self.path, lines)
