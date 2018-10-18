from lib import utils
from lib.utils import cached_property
from logging.config import dictConfig
import pathlib
import os
import definitions


class ConfigurationException(Exception):
    pass


class BaseConfigClass:

    def __init__(self, app_name, postfix='receiver'):
        self.app_name = app_name
        self.postfix = postfix

    @cached_property
    def receiver(self):
        raise NotImplementedError

    @cached_property
    def receiver_config(self):
        raise NotImplementedError

    @cached_property
    def message_manager_config(self):
        raise NotImplementedError

    @cached_property
    def message_manager(self):
        raise NotImplementedError

    @cached_property
    def protocol(self):
        raise NotImplementedError

    @cached_property
    def protocol_config(self):
        raise NotImplementedError

    def action_config(self, action_name, storage=True):
        return {
            'home': self.path_for_action(action_name),
        }

    def get_home(self, fallback=None):
        raise NotImplementedError

    def get_data_home(self, fallback=None):
        raise NotImplementedError

    def get_action_home(self, action_name):
        raise NotImplementedError

    def log_config(self):
        raise NotImplementedError

    @cached_property
    def format_dict(self):
        return {
            'testdir': definitions.TESTS_DIR,
            'develdir': definitions.ROOT_DIR,
            'userhome': definitions.USER_HOME,
            "~": definitions.USER_HOME,
            'osdatadir': definitions.OSDATA_DIR,
            'appname': self.app_name.replace(' ', '').lower(),
            'postfix': self.postfix.replace(' ', '').lower()
        }

    @cached_property
    def format_dict_with_home(self):
        format_dict = self.format_dict.copy()
        format_dict['home'] = str(self.home)
        return format_dict

    @cached_property
    def home(self):
        return pathlib.PurePath(self.get_home(fallback='%(userhome)s/%(appname)s') % self.format_dict)

    @cached_property
    def data_home(self):
        path = pathlib.PurePath(self.get_data_home(fallback='%(home)s/data') % self.format_dict_with_home)
        os.makedirs(path, exist_ok=True)
        return path

    def get_full_path(self, path):
        path = pathlib.PurePath(path % self.format_dict_with_home)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def path_for_action(self, action_name):
        format_dict = self.format_dict_with_home.copy()
        format_dict['datahome'] = str(self.data_home)
        format_dict['actionname'] = action_name
        path = pathlib.PurePath(self.get_action_home(action_name) % format_dict)
        os.makedirs(path, exist_ok=True)
        return path

    def configure_logging(self):
        config = self.log_config()
        logging_setup = False
        while not logging_setup:
            try:
                dictConfig(config)
                logging_setup = True
            except (FileNotFoundError, ValueError) as e:
                log_directory = os.path.dirname(e.filename)
                os.makedirs(log_directory, exist_ok=True)
