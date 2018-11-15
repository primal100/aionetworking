import binascii

from .base import BaseAction


class Action(BaseAction):
    """
    To store or display binary data in the format it was received.
    """
    action_name = 'Binary'
    default_data_dir = "Encoded"
    store_write_mode = 'wb'
    store_many_write_mode = 'ab'
    single_extension = None

    def get_file_extension(self, msg) -> str:
        return msg.file_extension

    def get_multi_file_extension(self, msg):
        return self.get_file_extension(msg)

    def print_msg(self, msg) -> str:
        return binascii.hexlify(msg.encoded).decode()
