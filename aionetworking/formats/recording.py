from dataclasses import dataclass
from .base import BaseMessageObject
from collections import namedtuple
from pathlib import Path
from .contrib.pickle import PickleCodec
from typing import AsyncGenerator


recorded_packet = namedtuple("recorded_packet", ["sent_by_server", "timestamp", "sender", "data"])


@dataclass
class BufferCodec(PickleCodec):
    log_msgs = False

    async def decode(self, encoded: bytes, **kwargs) -> recorded_packet:
        async for encoded, decoded in super().decode(encoded, **kwargs):
            yield encoded, recorded_packet(*decoded)

    async def encode(self, decoded: bytes, system_timestamp=None, **kwargs) -> bytes:
        if self.context:
            sender = self.context.get('address')
        else:
            sender = None
        packet_data = (
            False,
            system_timestamp,
            sender,
            decoded
        )
        return await super().encode(packet_data, **kwargs)


@dataclass
class BufferObject(BaseMessageObject):
    name = 'Buffer'
    codec_cls = BufferCodec


def get_recording_codec() -> PickleCodec:
    return BufferCodec(BufferObject)


async def get_recording(data: bytes) -> AsyncGenerator[recorded_packet, None]:
    codec = get_recording_codec()
    async for item in codec.decode_buffer(data):
        yield item.decoded


async def get_recording_from_file(path: Path) -> AsyncGenerator[recorded_packet, None]:
    codec = get_recording_codec()
    async for item in codec.from_file(path):
        yield item.decoded


