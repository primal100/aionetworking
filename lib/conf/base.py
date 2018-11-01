from lib.utils import cached_property, now_to_utc_string

from pathlib import Path


class ConfigurationException(Exception):
    pass


class BaseConfigClass:

    def __init__(self):
        import settings
        self.defaults = {
            'Testdir': settings.TESTS_DIR,
            'Develdir': settings.ROOT_DIR,
            'Userhome': settings.USER_HOME,
            "~": settings.USER_HOME,
            'Osdatadir': settings.OSDATA_DIR,
            'timestamp': now_to_utc_string()
        }
        self.defaults.update({
            'appname': settings.APP_NAME.replace(' ', '').lower(),
            'postfix': settings.POSTFIX.replace(' ', '').lower()
        })

    @cached_property
    def receiver(self):
        raise NotImplementedError

    @cached_property
    def message_manager_is_batch(self):
        raise NotImplementedError

    @cached_property
    def protocol(self):
        raise NotImplementedError

    def action_config(self, action_name: str, d: str, storage: bool=True):
        return {
            'home': self.path_for_action(action_name, d)
        }

    @cached_property
    def home(self):
        return self.get_home()

    def get_home(self):
        raise NotImplementedError

    def get_data_home(self):
        raise NotImplementedError

    def get_action_home(self, action_name: str, d: str) -> Path:
        raise NotImplementedError

    def configure_logging(self):
        raise NotImplementedError

    @cached_property
    def data_home(self) -> Path:
        path = self.get_data_home()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def path_for_action(self, action_name: str, d: str) -> Path:
        path = self.get_action_home(action_name, d)
        return path
