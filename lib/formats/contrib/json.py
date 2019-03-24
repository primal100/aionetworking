import json

from lib.formats.base import BaseCodec, BaseMessageObject


class JSONCodec(BaseCodec):
    """
    Decode & Encode JSON messages
    """

    def decode(self, encoded: bytes, **kwargs):
        pos = 0
        end = len(encoded)
        while pos < end:
            start = pos
            msg, pos = json.JSONDecoder().raw_decode(encoded, idx=pos)
            yield (encoded[start:pos], msg)

    def encode(self, decoded, **kwargs):
        return json.dumps(decoded)


class JSONObject(BaseMessageObject):
    codec_cls = JSONCodec




