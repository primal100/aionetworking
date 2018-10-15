from .base import BaseAction
from pprint import pformat


class Action(BaseAction):
    """
    To store or display ascii/unicode data in the decoded pythonic format
    """

    action_name = 'Decode'
    default_data_dir = "Decoded"
    store_write_mode = 'w+'

    def get_content(self, msg):
        return pformat(msg.decoded)

    def get_content_multi(self, msg):
        return self.get_content(msg) + '\n\n'

