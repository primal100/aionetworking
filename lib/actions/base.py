import os
import logging
from lib import utils
from lib.utils import underline

logger = logging.getLogger('messageManager')


class BaseAction:
    action_name = ''
    default_data_dir = ""
    store_write_mode = 'w+'
    store_many_write_mode = 'a'
    single_extension = "txt"
    multi_extension = "txt"

    @classmethod
    def from_config(cls, storage=True):
        import definitions
        config = definitions.CONFIG.action_config(cls.default_data_dir, storage=storage)
        return cls(storage=storage, **config)

    def __init__(self, storage=True, home=''):

        if storage:
            logger.info("Setting up action %s for storage" % self.action_name)
            self.base_path = home
            logger.info("Using directory %s for %s" % (self.base_path, self.action_name))
            os.makedirs(self.base_path, exist_ok=True)
        else:
            logger.info("Setting up action %s for print" % self.action_name)

    def get_content(self, msg):
        raise NotImplementedError

    def get_content_multi(self, msg):
        return self.get_content(msg)

    def print_msg(self, msg):
        return self.get_content(msg)

    def print(self, msg):
        if not msg.filter_by_action(self, True):
            print(underline("Message received from %s:" % msg.sender))
            print(self.print_msg(msg))
            print("")
        else:
            logger.debug("Message filtered for action %s print" % self.action_name)

    def do(self, msg):
        if not msg.filter_by_action(self, False):
            path = os.path.join(self.base_path, msg.storage_path_single)
            file_path = msg.unique_filename(path, self.get_file_extension(msg))
            logger.debug('Storing %s message in %s' % (self.action_name, file_path))
            with open(file_path, self.store_write_mode) as f:
                f.write(self.get_content(msg))
        else:
            logger.debug("Message filtered for action %s" % self.action_name)

    def get_file_extension(self, msg):
        return self.single_extension

    def get_multi_file_extension(self, msg):
        return self.multi_extension

    def writes_for_store_many(self, msgs):
        writes = {}
        for msg in msgs:
            if not msg.filter_by_action(self, False):
                file_name = msg.storage_filename_multiple + "." + self.get_multi_file_extension(msg)
                if file_name in writes:
                    writes[file_name] += self.get_content_multi(msg)
                else:
                    writes[file_name] = self.get_content_multi(msg)
        return writes

    def store_many(self, msgs):
        logger.debug('Storing %s messages for action %s' % (len(msgs), self.action_name))
        writes = self.writes_for_store_many(msgs)
        logger.debug('Storing in files %s' % list(writes.keys()))
        utils.write_to_files(self.base_path, self.store_many_write_mode, writes)

    def do_multiple(self, msgs):
        self.store_many(msgs)

