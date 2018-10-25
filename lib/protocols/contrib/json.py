import json

from lib.protocols.base import BaseProtocol


class BaseJSONProtocol(BaseProtocol):
    protocol_name = "json"
    binary = False

    """
    Manage JSON messages
    """

    supported_actions = ("text", "decode", "prettify", "summaries")

    def decode(self) -> bytes:
        return json.loads(self.encoded)
