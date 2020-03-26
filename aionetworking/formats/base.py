from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat

from aionetworking import settings
from aionetworking.context import context_cv
from aionetworking.logging.loggers import connection_logger_cv
from aionetworking.types.logging import ConnectionLoggerType
from aionetworking.utils import aone, dataclass_getstate, dataclass_setstate

from .protocols import MessageObject, Codec
from typing import AsyncGenerator, Any, Dict, Sequence, Type, Optional
from aionetworking.compatibility import Protocol
from aionetworking.types.formats import MessageObjectType, CodecType


def current_time() -> datetime.datetime:
    # Required to work with freeze_gun
    return datetime.datetime.now()


@dataclass
class BaseMessageObject(MessageObject, Protocol):
    name = None
    codec_cls = None
    id_attr = 'id'
    stats_logger = None

    encoded: bytes
    decoded: Any = None
    context: Dict[str, Any] = field(default_factory=context_cv.get, compare=False, repr=False, hash=False)
    parent_logger: ConnectionLoggerType = field(default_factory=connection_logger_cv.get, compare=False, hash=False, repr=False)
    system_timestamp: datetime = field(default_factory=current_time, compare=False, repr=False, hash=False)
    received: bool = field(default=True, compare=False)

    def __post_init__(self):
        self.logger = self.parent_logger.new_msg_logger(self)
        self.context = self.context or {}

    @property
    def received_or_sent(self) -> str:
        return "RECEIVED" if self.received else "SENT"

    @classmethod
    def _get_codec_kwargs(cls) -> Dict:
        return {}

    @classmethod
    def get_codec(cls, first_buffer_received: Optional[bytes] = None, **kwargs) -> CodecType:
        kwargs.update(cls._get_codec_kwargs())
        return cls.codec_cls(cls, **kwargs)

    @property
    def sender(self) -> str:
        return self.context.get('host', self.context.get('peer'))

    @property
    def address(self) -> str:
        return self.context['address']

    @property
    def peer(self) -> str:
        print(self.context)
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
    def timestamp(self) -> datetime.datetime:
        return self.system_timestamp

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
    log_msgs = True
    supports_notifications = False

    msg_obj: Type[MessageObjectType]
    context: Dict[str, Any] = field(default_factory=context_cv.get)
    logger: ConnectionLoggerType = field(default_factory=connection_logger_cv.get, compare=False, hash=False, repr=False)

    def __post_init__(self):
        self.context = self.context or {}

    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Sequence[bytes, Any], None]:
        yield encoded, encoded

    async def encode(self, decoded: Any, **kwargs) -> bytes:
        return decoded

    def decode_one(self, encoded: bytes, **kwargs) -> Any:
        return aone(self.decode(encoded, **kwargs))

    async def _from_buffer(self, encoded: bytes, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        _context = self.context.copy()
        _context.update(kwargs.pop('context', {}))
        async for encoded, decoded in self.decode(encoded, **kwargs):
            yield self.msg_obj(encoded, decoded, context=self.context, parent_logger=self.logger, **kwargs)

    async def decode_buffer(self, encoded: bytes, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        i = 0
        async for msg in self._from_buffer(encoded, **kwargs):
            if self.log_msgs:
                self.logger.on_msg_decoded(msg)
            yield msg
            i += 1
        self.logger.on_buffer_decoded(encoded, i)

    async def encode_obj(self, decoded: Any, **kwargs) -> MessageObjectType:
        try:
            encoded = await self.encode(decoded, **kwargs)
            return self.msg_obj(encoded, decoded, context=self.context, received=False,
                                parent_logger=self.logger, **kwargs)
        except Exception as exc:
            obj = self.msg_obj(b'', decoded, context=self.context, parent_logger=self.logger, received=False, **kwargs)
            self.logger.on_encode_failed(obj, exc)

    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        self.logger.debug('Creating new %s messages from %s', self.codec_name, file_path)
        async with settings.FILE_OPENER(file_path, self.read_mode) as f:
            encoded = await f.read()
        async for item in self.decode_buffer(encoded, **kwargs):
            yield item

    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType:
        return await aone(self.from_file(file_path, **kwargs))


