from __future__ import annotations

import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat

from lib import settings
from lib.conf.context import context_cv
from lib.conf.logging import ConnectionLogger, connection_logger_cv
from lib.networking.connections_manager import connections_manager
from lib.utils import aone, dataclass_getstate, dataclass_setstate

from .protocols import MessageObject, Codec
from typing import AsyncGenerator, Any, Dict, Sequence, Type
from lib.compatibility import Protocol
from .types import MessageObjectType, CodecType


@dataclass
class BaseMessageObject(MessageObject, Protocol):
    name = None
    codec_cls = None
    id_attr = 'id'
    stats_logger = None

    encoded: bytes
    decoded: Any = None
    context: Dict[str, Any] = field(default_factory=context_cv.get, compare=False, repr=False, hash=False)
    logger: ConnectionLogger = field(default_factory=connection_logger_cv.get, compare=False, hash=False, repr=False)
    received_timestamp: datetime = field(default_factory=datetime.now, compare=False, repr=False, hash=False)

    def __post_init__(self):
        pass

    @classmethod
    def swap_cls(cls, name) -> Type[MessageObjectType]:
        from lib import definitions
        return definitions.DATA_FORMATS[name]

    @classmethod
    def _get_codec_kwargs(cls) -> Dict:
        return {}

    @classmethod
    def get_codec(cls, **kwargs) -> CodecType:
        kwargs.update(cls._get_codec_kwargs())
        return cls.codec_cls(cls, **kwargs)

    @property
    def peer(self) -> str:
        return self.context['alias']

    @property
    def full_peer(self) -> str:
        return self.context['peer']

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def get(self, item, default=None):
        try:
            return self.decoded[item]
        except KeyError:
            return default

    def __getitem__(self, item):
        if isinstance(self.decoded, (list, tuple, dict)):
            return self.decoded[item]

    @property
    def uid(self) -> Any:
        try:
            return self.decoded[self.id_attr]
        except (AttributeError, KeyError, TypeError):
            return id(self)

    @property
    def request_id(self) -> Any:
        try:
            return self.decoded.get(self.id_attr)
        except (AttributeError, KeyError):
            return None

    @property
    def pformat(self) -> str:
        return pformat(self.decoded)

    @property
    def timestamp(self) -> datetime:
        return self.received_timestamp

    def filter(self) -> bool:
        return False

    def __str__(self):
        return f"{self.name} {self.uid}"


@dataclass
class BaseCodec(Codec):
    codec_name = ''
    read_mode = 'rb'
    write_mode = 'wb'
    append_mode = 'ab'

    msg_obj: Type[MessageObjectType]
    context: Dict[str, Any] = field(default_factory=context_cv.get)
    logger: ConnectionLogger = field(default_factory=connection_logger_cv.get, compare=False, hash=False, repr=False)

    def __post_init__(self):
        pass

    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Sequence[bytes, Any], None]:
        yield (encoded, encoded)

    def encode(self, decoded: Any, **kwargs) -> bytes:
        return decoded

    def decode_one(self, encoded: bytes, **kwargs) -> Any:
        return aone(self.decode(encoded, **kwargs))

    async def _from_buffer(self, encoded: bytes, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        async for encoded, decoded in self.decode(encoded, **kwargs):
            yield self.msg_obj(encoded, decoded, context=self.context, logger=self.logger, **kwargs)

    async def decode_buffer(self, encoded: bytes, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        i = 0
        async for msg in self._from_buffer(encoded, **kwargs):
            self.logger.on_msg_decoded(msg)
            yield msg
            i += 1
        self.logger.on_buffer_decoded(i)

    def from_decoded(self, decoded: Any, **kwargs) -> MessageObjectType:
        return self.msg_obj(self.encode(decoded, **kwargs), decoded, context=self.context, logger=self.logger, **kwargs)

    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        self.logger.debug('Creating new %s messages from %s', self.codec_name, file_path)
        async with settings.FILE_OPENER(file_path, self.read_mode) as f:
            encoded = await f.read()
        async for item in self.decode_buffer(encoded, **kwargs):
            yield item

    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType:
        return await aone(self.from_file(file_path, **kwargs))


