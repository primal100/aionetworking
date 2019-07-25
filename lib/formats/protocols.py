from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat

from lib import settings
from lib.conf.logging import ConnectionLogger, connection_logger_receiver
from lib.types import Type
from lib.utils import Record, aone

from typing import AsyncGenerator, Generator, Any, AnyStr, MutableMapping, Sequence, Generic, TypeVar
from typing_extensions import Protocol


class MessageObjectProtocol(Protocol):

    @classmethod
    def _get_codec_kwargs(cls) -> MutableMapping:
        return {}

    @classmethod
    def get_codec(cls, **kwargs) -> CodecType:
        kwargs.update(cls._get_codec_kwargs())
        return cls.codec_cls(cls, **kwargs)

    @property
    def sender(self) -> str:
        return self.context['alias']

    @property
    def uid(self) -> Any:
        try:
            return self.decoded[self.id_attr]
        except (AttributeError, KeyError):
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

    def processed(self) -> None:
        if self.stats_logger:
            self.stats_logger.on_message_processed(self)

    def __str__(self):
        return f"{self.name} {self.uid}"


@dataclass
class BufferObject(BaseMessageObject):
    _record = Record()

    @property
    def record(self) -> bytes:
        return self._record.pack_client_msg(self)


MessageObjectType = TypeVar('MessageObjectType', bound=BaseMessageObject)


@dataclass
class BaseCodec(Generic[MessageObjectType]):
    codec_name = ''
    read_mode = 'rb'
    write_mode = 'wb'
    append_mode = 'ab'

    msg_obj: Type[MessageObjectType]
    context: MutableMapping = field(default_factory=dict)
    logger: ConnectionLogger = field(default=connection_logger_receiver, compare=False, hash=False, repr=False)

    def set_context(self, context, logger=None):
        self.context.update(context)
        if logger:
            self.logger = logger

    def decode(self, encoded: bytes, **kwargs) -> Generator[Sequence[AnyStr, Any], None, None]:
        yield (encoded, encoded)

    def encode(self, decoded, **kwargs):
        return decoded

    def from_buffer(self, encoded, **kwargs) -> Generator[MessageObjectType, None, None]:
        for encoded, decoded in self.decode(encoded):
            yield self.msg_obj(encoded, decoded, context=self.context, logger=self.logger, **kwargs)

    def decode_buffer(self, encoded: AnyStr, **kwargs) -> Generator[MessageObjectType, None, None]:
        for msg in self.from_buffer(encoded, **kwargs):
            self.logger.on_msg_decoded(msg)
            yield msg

    def from_decoded(self, decoded, **kwargs) -> MessageObjectType:
        return self.msg_obj(self.encode(decoded), decoded, context=self.context, **kwargs)

    def create_msg(self, decoded, **kwargs):
        encoded = self.encode(decoded, **kwargs)
        return self.msg_obj(encoded, decoded=decoded, context=self.context, **kwargs)

    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        self.logger.debug('Creating new %s message from %s', self.codec_name, file_path)
        async with settings.FILE_OPENER(file_path, self.read_mode) as f:
            encoded = await f.read()
        for item in self.from_buffer(encoded, **kwargs):
            yield item

    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType:
        return await aone(self.from_file(file_path, **kwargs))


class BaseTextCodec(BaseCodec):
    read_mode = 'r'
    write_mode = 'w'
    append_mode = 'a'


CodecType = TypeVar('CodecType', bound=BaseCodec)
