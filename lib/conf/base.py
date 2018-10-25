from lib.utils import cached_property, now_to_utc_string
from pathlib import Path
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
        'timestamp': now_to_utc_string()
    }

    def __init__(self, app_name: str, postfix: str='receiver'):
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
    def message_manager_is_batch(self):
        raise NotImplementedError

    @cached_property
    def message_manager_config(self):
        raise NotImplementedError

    @cached_property
    def protocol(self):
        raise NotImplementedError

    @cached_property
    def protocol_config(self):
        raise NotImplementedError

    def action_config(self, action_name: str, storage: bool=True):
        return {
            'home': self.path_for_action(action_name),
        }

    @cached_property
    def home(self):
        raise NotImplementedError

    def get_home(self):
        raise NotImplementedError

    def get_data_home(self):
        raise NotImplementedError

    def get_action_home(self, action_name: str) -> Path:
        raise NotImplementedError

    def configure_logging(self):
        raise NotImplementedError

    @cached_property
    def data_home(self) -> Path:
        path = self.get_data_home()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def path_for_action(self, action_name: str) -> Path:
        path = self.get_action_home(action_name)
        path.mkdir(parents=True, exist_ok=True)
        return path
