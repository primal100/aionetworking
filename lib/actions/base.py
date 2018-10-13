import os
from lib import utils
from lib.utils import underline


class BaseAction:
    action_name = ''
    default_home = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "data")
    default_data_dir = ""
    store_write_mode = 'w+'
    store_many_write_mode = 'a'
    single_extension = "txt"
    multi_extension = "txt"

    def __init__(self, app_name, config, storage=True):

        self.APP_NAME = app_name
        if storage:
            home = config.get('home', utils.data_directory(self.APP_NAME))
            data_dir = config.get('%s_data_dir' % self.action_name) or self.default_data_dir
            self.base_path = os.path.join(home, data_dir)
            os.makedirs(self.base_path, exist_ok=True)

    def get_content(self, msg):
        raise NotImplementedError

    def get_content_multi(self, msg):
        return self.get_content(msg)

    def print_msg(self, msg):
        return self.get_content(msg)

    def print(self, msg):
        print(underline("Message received from %s:" % msg.sender))
        print(self.print_msg(msg))
        print("")

    def do(self, msg):
        path = os.path.join(self.base_path, msg.storage_path_single)
        file_path = msg.unique_filename(path, self.get_file_extension(msg))
        with open(file_path, self.store_write_mode) as f:
            f.write(self.get_content(msg))

    def get_file_extension(self, msg):
        return self.single_extension

    def get_multi_file_extension(self, msg):
        return self.multi_extension

    def writes_for_store_many(self, msgs):
        writes = {}
        for msg in msgs:
            file_name = msg.storage_filename_multiple + "." + self.get_multi_file_extension(msg)
            if file_name in writes:
                writes[file_name] += self.get_content_multi(msg)
            else:
                writes[file_name] = self.get_content_multi(msg)
        return writes

    def store_many(self, msgs):
        writes = self.writes_for_store_many(msgs)
        utils.write_to_files(self.base_path, self.store_many_write_mode, writes)

    def do_multiple(self, msgs):
        print(self.action_name)
        self.store_many(msgs)

