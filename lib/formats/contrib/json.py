from __future__ import annotations
import io
import json
from dataclasses import dataclass

from lib.formats.base import BaseTextCodec, BaseMessageObject

from typing import AnyStr, Any


@dataclass
class JSONCodec(BaseTextCodec):
    """
    Decode & Encode JSON messages
    """

    def decode(self, encoded: AnyStr, **kwargs) -> [AnyStr, Any]:
        pos = 0
        end = len(encoded)
        while pos < end:
            start = pos
            msg, pos = json.JSONDecoder().raw_decode(encoded, idx=pos)
            yield (encoded[start:pos], msg)

    def encode(self, decoded: Any, **kwargs) -> AnyStr:
        return json.dumps(decoded)


@dataclass
class JSONObject(BaseMessageObject):
    name = 'JSON'
    codec_cls = JSONCodec





