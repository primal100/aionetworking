
import io
import pickle
from dataclasses import dataclass

from aionetworking.formats.base import BaseCodec, BaseMessageObject

from typing import Any, AsyncGenerator, Tuple


@dataclass
class PickleCodec(BaseCodec):
    protocol = 4
    """
    Decode & Encode Pickle messages
    """

    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Tuple[bytes, Any], None]:
        data = io.BytesIO(encoded)
        num_bytes = len(encoded)
        current_pos = 0
        while current_pos < num_bytes:
            start_pos = data.tell()
            decoded = pickle.load(data)
            current_pos = data.tell()
            yield encoded[start_pos:current_pos], decoded

    async def encode(self, decoded: Any, **kwargs) -> bytes:
        return pickle.dumps(decoded, protocol=self.protocol)


@dataclass
class PickleObject(BaseMessageObject):
    name = 'Pickle'
    codec_cls = PickleCodec
