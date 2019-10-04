from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass

from lib.formats.base import BaseCodec, BaseMessageObject

from typing import Any, AsyncGenerator, Tuple


@dataclass
class JSONCodec(BaseCodec):
    codec_name = 'json'

    """
    Decode & Encode JSON text messages
    """

    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Tuple[bytes, Any], None]:
        pos = 0
        end = len(encoded)
        while pos < end:
            start = pos
            data = encoded.decode()
            msg, pos = json.JSONDecoder().raw_decode(data, idx=pos)
            yield (encoded[start:pos], msg)

    def encode(self, decoded: Any, **kwargs) -> bytes:
        return json.dumps(decoded).encode()


@dataclass
class JSONObject(BaseMessageObject):
    name = 'JSON'
    codec_cls = JSONCodec
