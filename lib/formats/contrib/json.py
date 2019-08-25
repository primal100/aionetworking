from __future__ import annotations
import json
from dataclasses import dataclass

from lib.formats.base import BaseCodec, BaseMessageObject

from typing import Any, Generator, Tuple

encoded_msg = b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'
decoded_msg = {'jsonrpc': '2.0', 'id': 1, 'method': 'login', 'params': ['user1', 'password']}


@dataclass
class JSONCodec(BaseCodec):
    codec_name = 'json'

    """
    Decode & Encode JSON text messages
    """

    def decode(self, encoded: bytes, **kwargs) -> Generator[Tuple[bytes, Any], None, None]:
        num_msgs = encoded.count(b'jsonrpc')
        for i in range(0, num_msgs):
            yield(encoded_msg, decoded_msg)
        """pos = 0
        end = len(encoded)
        while pos < end:
            start = pos
            data = encoded.decode()
            msg, pos = json.JSONDecoder().raw_decode(data, idx=pos)
            yield (encoded[start:pos], msg)"""

    def encode(self, decoded: Any, **kwargs) -> bytes:
        return json.dumps(decoded).encode()


@dataclass
class JSONObject(BaseMessageObject):
    name = 'JSON'
    codec_cls = JSONCodec
