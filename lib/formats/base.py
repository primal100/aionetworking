from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat

from lib import settings
from lib.conf.logging import ConnectionLogger, connection_logger_receiver
from lib.networking.connections_manager import connections_manager
from lib.utils import Record, aone

from .protocols import MessageObject, Codec
from typing import AsyncGenerator, Generator, Any, AnyStr, Dict, Sequence, Type
from lib.compatibility import Protocol
from .types import MessageObjectType, CodecType


@dataclass
class BaseMessageObject(MessageObject, Protocol):
    name = None
    binary = True
    codec_cls = None
    id_attr = 'id'
    stats_logger = None

    encoded: AnyStr
    decoded: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    logger: ConnectionLogger = field(default_factory=connection_logger_receiver, compare=False, hash=False, repr=False)
    received_timestamp: datetime = field(default_factory=datetime.now, compare=False)

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
    def sender(self) -> str:
        return self.context['alias']

    @property
    def full_sender(self) -> str:
        return self.context['peer']

    def get(self, item, default=None):
        try:
            return self.decoded[item]
        except KeyError:
            return default

    def __getitem__(self, item):
        if isinstance(self.decoded, (list, tuple, dict)):
            return self.decoded[item]

    def is_subscribed(self, subscribe_key: Any) -> bool:
        return connections_manager.peer_is_subscribed(self.full_sender, subscribe_key)

    def subscribe(self, subscribe_key: Any) -> None:
        self.logger.debug('Subscribing to key %s', subscribe_key)
        connections_manager.subscribe(self.full_sender, subscribe_key)

    def unsubscribe(self, subscribe_key: Any) -> None:
        self.logger.debug('Unsubscribing from key %s', subscribe_key)
        connections_manager.unsubscribe(self.full_sender, subscribe_key)

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
        self.logger.on_msg_processed(len(self.encoded))

    def __str__(self):
        return f"{self.name} {self.uid}"


@dataclass
class BufferObject(BaseMessageObject):
    _record = Record()

    @property
    def record(self) -> bytes:
        return self._record.pack_client_msg(self)

    def processed(self) -> None:
        pass


@dataclass
class BaseCodec(Codec):
    codec_name = ''
    read_mode = 'rb'
    write_mode = 'wb'
    append_mode = 'ab'

    msg_obj: Type[MessageObjectType]
    context: Dict[str, Any] = field(default_factory=dict)
    logger: ConnectionLogger = field(default_factory=connection_logger_receiver, compare=False, hash=False, repr=False)

    def decode(self, encoded: bytes, **kwargs) -> Generator[Sequence[AnyStr, Any], None, None]:
        yield (encoded, encoded)

    def encode(self, decoded: Any, **kwargs) -> AnyStr:
        return decoded

    def decode_one(self, encoded:bytes, **kwargs) -> Any:
        return next(self.decode(encoded, **kwargs))[1]

    def _from_buffer(self, encoded: AnyStr, **kwargs) -> Generator[MessageObjectType, None, None]:
        for encoded, decoded in self.decode(encoded):
            yield self.msg_obj(encoded, decoded, context=self.context, logger=self.logger, **kwargs)

    def decode_buffer(self, encoded: AnyStr, **kwargs) -> Generator[MessageObjectType, None, None]:
        for msg in self._from_buffer(encoded, **kwargs):
            self.logger.on_msg_decoded(msg)
            yield msg

    def from_decoded(self, decoded: Any, **kwargs) -> MessageObjectType:
        return self.msg_obj(self.encode(decoded), decoded, context=self.context, **kwargs)

    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        self.logger.debug('Creating new %s message from %s', self.codec_name, file_path)
        async with settings.FILE_OPENER(file_path, self.read_mode) as f:
            encoded = await f.read()
        for item in self.decode_buffer(encoded, **kwargs):
            yield item

    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType:
        return await aone(self.from_file(file_path, **kwargs))


class BaseTextCodec(BaseCodec):
    read_mode = 'r'
    write_mode = 'w'
    append_mode = 'a'

