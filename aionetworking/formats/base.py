import datetime
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat

from aionetworking import settings
from aionetworking.logging.loggers import get_connection_logger_receiver
from aionetworking.types.logging import ConnectionLoggerType
from aionetworking.utils import aone, dataclass_getstate, dataclass_setstate

from .protocols import MessageObject, Codec
from typing import AsyncGenerator, Any, Dict, Sequence, Type, Optional
from aionetworking.compatibility import Protocol
from aionetworking.types.formats import MessageObjectType, CodecType
from aionetworking.types.networking import BaseContext


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
    context: BaseContext = field(default_factory=dict, compare=False, repr=False, hash=False)
    parent_logger: ConnectionLoggerType = field(default_factory=get_connection_logger_receiver, compare=False, hash=False, repr=False)
    system_timestamp: datetime = field(default_factory=current_time, compare=False, repr=False, hash=False)
    received: bool = field(default=True, compare=False, repr=False)

    def __post_init__(self):
        self.logger = self.parent_logger.new_msg_logger(self)

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
    def receiver(self) -> str:
        return self.full_receiver.split(':')[0]

    @property
    def full_receiver(self) -> str:
        return self.context.get('own')

    @property
    def address(self) -> str:
        return self.context['address']

    @property
    def full_sender(self) -> str:
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
        return pformat(self.decoded, compact=True, width=120)

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
    context: BaseContext = field(default_factory=dict)
    logger: ConnectionLoggerType = field(default_factory=get_connection_logger_receiver, compare=False, hash=False, repr=False)

    def __post_init__(self):
        self.context = self.context or {}

    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Sequence[bytes], None]:
        yield encoded, encoded

    async def encode(self, decoded: Any, **kwargs) -> bytes:
        return decoded

    async def decode_one(self, encoded: bytes, **kwargs) -> Any:
        return await aone(self.decode(encoded, **kwargs))

    async def create_object(self, encoded: bytes, decoded: Any, **kwargs) -> MessageObjectType:
        return self.msg_obj(encoded, decoded, **kwargs)

    async def _from_buffer(self, encoded: bytes, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        async for encoded, decoded in self.decode(encoded, **kwargs):
            yield await self.create_object(encoded, decoded, parent_logger=self.logger, **kwargs)

    async def decode_buffer(self, encoded: bytes, context: BaseContext = None, source: str = 'buffer',
                            **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        if context:
            complete_context = self.context.copy()
            complete_context.update(context)
        else:
            complete_context = self.context
        i = 0
        async for msg in self._from_buffer(encoded, context=complete_context, **kwargs):
            if self.log_msgs:
                self.logger.on_msg_decoded(msg)
            yield msg
            i += 1
        self.logger.on_buffer_decoded(encoded, i, source=source)

    async def encode_obj(self, decoded: Any, **kwargs) -> MessageObjectType:
        try:
            encoded = await self.encode(decoded, **kwargs)
            return await self.create_object(encoded, decoded, context=self.context, received=False,
                                            parent_logger=self.logger, **kwargs)
        except Exception as exc:
            obj = await self.create_object(b'', decoded, context=self.context, parent_logger=self.logger, received=False, **kwargs)
            self.logger.on_encode_failed(obj, exc)

    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        self.logger.debug('Loading new %s messages from %s', self.codec_name, file_path)
        async with settings.FILE_OPENER(file_path, self.read_mode) as f:
            encoded = await f.read()
        async for item in self.decode_buffer(encoded, source=f"file {file_path}", **kwargs):
            yield item

    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType:
        return await aone(self.from_file(file_path, **kwargs))


