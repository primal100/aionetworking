from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass

from lib.formats.base import BaseCodec, BaseMessageObject

from typing import Any, AsyncGenerator, Tuple

encoded_msg = b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'
decoded_msg = {'jsonrpc': '2.0', 'id': 1, 'method': 'login', 'params': ['user1', 'password']}


@dataclass
class JSONCodec(BaseCodec):
    codec_name = 'json'

    """
    Decode & Encode JSON text messages
    """

    def _decode(self, encoded: bytes):
        return [(encoded_msg, decoded_msg) for _ in range(0, encoded.count(b'jsonrpc'))]

    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Tuple[bytes, Any], None]:
        for item in await asyncio.get_event_loop().run_in_executor(None, self._decode, encoded):
            yield item
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
