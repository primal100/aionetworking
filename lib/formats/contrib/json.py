from __future__ import annotations
import json
from dataclasses import dataclass

from lib.formats.base import BaseCodec, BaseMessageObject

from typing import AnyStr, Any, Generator, Tuple


@dataclass
class JSONCodec(BaseCodec):
    read_mode = 'r'
    write_mode = 'w'
    append_mode = 'a'

    """
    Decode & Encode JSON text messages
    """

    def decode(self, encoded: AnyStr, **kwargs) -> Generator[Tuple[AnyStr, Any], None, None]:
        pos = 0
        end = len(encoded)
        while pos < end:
            start = pos
            msg, pos = json.JSONDecoder().raw_decode(encoded, idx=pos)
            yield (encoded[start:pos], msg)

    def encode(self, decoded: Any, **kwargs) -> AnyStr:
        return json.dumps(decoded)


@dataclass
class JSONBCodec(JSONCodec):
    read_mode = 'rb'
    write_mode = 'wb'
    append_mode = 'ab'

    """
    Decode & Encode JSON binary messages
    """

    def decode(self, encoded: AnyStr, **kwargs) -> Generator[Tuple[AnyStr, Any], None, None]:
        encoded = encoded.decode()
        for encoded, decoded in super().decode(encoded, **kwargs):
            yield encoded.encode(), decoded

    def encode(self, decoded: Any, **kwargs) -> AnyStr:
        return super().encode(decoded, **kwargs).encode()


@dataclass
class JSONObject(BaseMessageObject):
    name = 'JSON'
    codec_cls = JSONCodec


@dataclass
class JSONBObject(BaseMessageObject):
    name = 'JSON'
    codec_cls = JSONBCodec
