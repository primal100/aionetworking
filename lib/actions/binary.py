from .base import BaseAction
from lib import utils
import binascii


class Action(BaseAction):
    """
    To store or display binary data in the format it was received.
    """
    action_name = 'Binary'
    default_data_dir = "Encoded"
    store_write_mode = 'wb+'
    store_many_write_mode = 'ab+'

    def get_content(self, msg):
        return msg.encoded

    def get_content_multi(self, msg):
        return utils.pack_binary(self.get_content(msg))

    def get_file_extension(self, msg):
        return msg.file_extension

    def get_multi_file_extension(self, msg):
        return self.get_file_extension(msg) + "MULTI"

    def print_msg(self, msg):
        return binascii.hexlify(msg.encoded).decode()
