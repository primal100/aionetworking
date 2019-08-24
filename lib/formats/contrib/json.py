from __future__ import annotations
import json
from dataclasses import dataclass

from lib.formats.base import BaseCodec, BaseMessageObject

from typing import Any, Generator, Tuple


@dataclass
class JSONCodec(BaseCodec):
    codec_name = 'json'

    """
    Decode & Encode JSON text messages
    """

    def decode(self, encoded: bytes, **kwargs) -> Generator[Tuple[bytes, Any], None, None]:
        pos = 0
        end = len(encoded)
        while pos < end:
            start = pos
            msg, pos = json.JSONDecoder().raw_decode(encoded.decode(), idx=pos)
            yield (encoded[start:pos], msg)

    def encode(self, decoded: Any, **kwargs) -> bytes:
        return json.dumps(decoded).encode()


@dataclass
class JSONObject(BaseMessageObject):
    name = 'JSON'
    codec_cls = JSONCodec
