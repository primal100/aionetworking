from lib.utils import cached_property
from logging.config import dictConfig
import pathlib
import os
import definitions


class ConfigurationException(Exception):
    pass


class BaseConfigClass:
    defaults = {
        'Testdir': definitions.TESTS_DIR,
        'Develdir': definitions.ROOT_DIR,
        'Userhome': definitions.USER_HOME,
        "~": definitions.USER_HOME,
        'Osdatadir': definitions.OSDATA_DIR,
    }

    def __init__(self, app_name, postfix='receiver'):
        self.defaults.update({
            'appname': app_name.replace(' ', '').lower(),
            'postfix': postfix.replace(' ', '').lower()
        })

    @cached_property
    def receiver(self):
        raise NotImplementedError

    @cached_property
    def receiver_config(self):
        raise NotImplementedError

    @cached_property
    def client_config(self):
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

    def get_home(self):
        raise NotImplementedError

    def get_data_home(self):
        raise NotImplementedError

    def get_action_home(self, action_name):
        raise NotImplementedError

    def log_config(self):
        raise NotImplementedError

    @cached_property
    def home(self):
        return pathlib.PurePath(self.get_home())

    @cached_property
    def data_home(self):
        path = pathlib.PurePath(self.get_data_home())
        os.makedirs(str(path), exist_ok=True)
        return path

    def path_for_action(self, action_name):
        path = pathlib.PurePath(self.get_action_home(action_name))
        os.makedirs(str(path), exist_ok=True)
        return path

    def configure_logging(self):
        config = self.log_config()
        dictConfig(config)
