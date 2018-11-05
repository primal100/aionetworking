import binascii
from .base import BaseRawAction
from lib import utils


class Action(BaseRawAction):
    """
    To store or display binary data in the format it was received.
    """
    action_name = 'Binary'
    default_data_dir = "Encoded"
    store_write_mode = 'wb+'
    store_many_write_mode = 'ab+'

    def get_content(self, data) -> bytes:
        return data

    def get_content_multi(self, data) -> bytes:
        return utils.pack_variable_len_string(self.get_content(data))

    def get_file_extension(self, data) -> str:
        return "SINGLE"

    def get_multi_file_extension(self, data):
        return "MULTI"

    def print_msg(self, data) -> str:
        return binascii.hexlify(data).decode()
