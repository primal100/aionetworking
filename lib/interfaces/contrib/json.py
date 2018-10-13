import json

from lib.interfaces.base import BaseMessage

class BaseJSONInterface(BaseMessage):
    interface_name = "json"
    read_mode = 'r'

    """
    Manage JSON messages
    """

    supported_actions = ("text", "decode", "prettify", "summaries")

    def decode(self):
        return json.loads(self.encoded)
