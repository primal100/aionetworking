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
    def interface(self):
        raise NotImplementedError

    @property
    def interface_config(self):
        raise NotImplementedError

    def action_config(self, action_name, storage=False):
        raise NotImplementedError