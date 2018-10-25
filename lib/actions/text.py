from .base import BaseAction
from pprint import pformat


class Action(BaseAction):
    """
    To store or display ascii/unicode data in the format it was received.
    """

    action_name = 'Text'
    default_data_dir = "Encoded"

    def get_content(self, msg):
        return msg.encoded

    def get_content_multi(self, msg):
        return self.get_content(msg) + '\n'

    def print_msg(self, msg) -> str:
        return pformat(self.get_content(msg))

    def get_file_extension(self, msg) -> str:
        return msg.file_extension

    def get_multi_file_extension(self, msg) -> str:
        return self.get_file_extension(msg)
