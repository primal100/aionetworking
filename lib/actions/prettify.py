from .decode import Action as BaseStoreAction
from lib.utils import store_dicts, print_dicts


class Action(BaseStoreAction):
    
    """
    To store or display prettified versions of received data
    """

    action_name = 'Prettify'
    default_data_dir = "Prettified"
    store_write_mode = 'w+'

    def get_content(self, msg):
        return store_dicts(msg.prettified)

    def get_content_multi(self, msg):
        return self.get_content(msg)

    def print_msg(self, msg) -> str:
        return print_dicts(msg.prettified)
