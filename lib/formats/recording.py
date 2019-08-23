from dataclasses import dataclass
from .base import BaseMessageObject
from collections import namedtuple
from pathlib import Path
from .contrib.pickle import PickleCodec
from typing import AnyStr, Any, Generator, AsyncGenerator, Sequence


recorded_packet = namedtuple("recorded_packet", ["sent_by_server", "timestamp", "sender", "is_bytes", "data"])


@dataclass
class BufferCodec(PickleCodec):

    def decode(self, encoded: bytes, **kwargs) -> recorded_packet:
        for encoded, decoded in super().decode(encoded, **kwargs):
            yield encoded, recorded_packet(*decoded)

    def encode(self, decoded: AnyStr, received_timestamp=None, **kwargs) -> bytes:
        if self.context:
            sender = self.context['alias']
        else:
            sender = None
        if isinstance(decoded, bytes):
            is_bytes = True
            data = decoded
        else:
            is_bytes = False
            data = decoded.encode()
        packet_data = (
            False,
            received_timestamp,
            sender,
            is_bytes,
            data
        )
        return super().encode(packet_data, **kwargs)


@dataclass
class BufferObject(BaseMessageObject):
    name = 'Buffer'
    codec_cls = BufferCodec


def get_recording_codec() -> PickleCodec:
    return BufferCodec(BufferObject)


def get_recording(data: bytes) -> Generator[recorded_packet, None, None]:
    codec = get_recording_codec()
    for item in codec.decode_buffer(data):
        yield item.decoded


async def get_recording_from_file(path: Path) -> AsyncGenerator[recorded_packet, None]:
    codec = get_recording_codec()
    async for item in codec.from_file(path):
        yield item.decoded


