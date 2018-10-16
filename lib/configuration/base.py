class ConfigurationException(Exception):
    pass


class BaseConfigClass:

    def __init__(self, config_meta):
        self.config_meta = config_meta

    @property
    def receiver(self):
        raise NotImplementedError

    @property
    def message_manager_config(self):
        raise NotImplementedError

    @property
    def message_manager(self):
        raise NotImplementedError

    @property
    def protocol(self):
        raise NotImplementedError

    @property
    def protocol_config(self):
        raise NotImplementedError

    def action_config(self, app_name, action_name, storage=False):
        raise NotImplementedError
