from abc import ABC
import asyncio
from datetime import datetime
from dataclasses import field
import logging
from pathlib import Path
from pprint import pformat

from pydantic.dataclasses import dataclass

from lib import settings
from lib.conf.logging import Logger
from lib.types import Type
from lib.utils import Record

from typing import Any, AnyStr, MutableMapping, Sequence



class EmbeddedDict(dict):
    def __getattr__(self, item):
        return self.get(item, None)

    def __getitem__(self, item):
        return self.__getattr__(item)


@dataclass
class BaseMessageObject(ABC):
    name = None
    binary = True
    supports_responses = False
    codec_cls = None
    id_attr = 'id'

    encoded: AnyStr
    decoded: Any = None
    context: dict = field(default_factory=dict)
    logger: Logger = 'receiver'
    received_timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def swap_cls(cls, name):
        from lib import definitions
        return definitions.DATA_FORMATS[name]

    @classmethod
    def get_codec(cls, **kwargs):
        return cls.codec_cls(cls, *cls.get_codec_args(), **kwargs)

    @property
    def sender(self):
        return self.context['alias']

    def __getattr__(self, item):
        val = self.decoded.get(item, None)
        if isinstance(val, dict):
            return EmbeddedDict(val)
        return val

    def __getitem__(self, item):
        return self.__getattr__(item)

    @classmethod
    def get_codec_args(cls):
        return ()

    @property
    def uid(self):
        try:
            return self.decoded[self.id_attr]
        except KeyError:
            return id(self)

    @property
    def request_id(self):
        return self.uid

    @property
    def pformat(self) -> str:
        return pformat(self.decoded)

    @property
    def timestamp(self) -> datetime:
        return self.received_timestamp

    def filter(self):
        return False

    def processed(self):
        if self.stats_logger:
            self.stats_logger.on_message_processed(self)

    def __str__(self):
        return f"{self.message_type} message {self.uid}"


class BufferObject(BaseMessageObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._record = Record()

    @property
    def record(self) -> bytes:
        return self._record.pack_client_msg(self)


class BaseCodec:
    codec_name = ''
    read_mode = 'rb'
    write_mode = 'wb'
    append_mode = 'ab'
    logger_name = 'receiver'

    def __init__(self, msg_obj: Type[BaseMessageObject], context: MutableMapping = None, logger=None):
        self.msg_obj = msg_obj
        self.context = context or {}
        self.logger = logger or logging.getLogger(self.logger_name)

    def set_context(self, context, logger=None):
        self.context.update(context)
        if logger:
            self.logger = logger

    async def read_file(self, file_path: Path):
        async with settings.FILE_OPENER(file_path, self.read_mode) as f:
            return await f.read()

    async def from_file(self, file_path: Path, **kwargs):
        self.logger.debug('Creating new %s message from %s', self.codec_name, file_path)
        encoded = await asyncio.create_task(self.read_file(file_path))
        return self.from_buffer(encoded, **kwargs)

    def from_buffer(self, encoded, **kwargs) -> Sequence:
        return [self.msg_obj(encoded, decoded, **kwargs) for encoded, decoded in self.decode(encoded)]

    def from_decoded(self, decoded, **kwargs):
        return self.msg_obj(self.encode(decoded), decoded, **kwargs)

    def create_msg(self, decoded, **kwargs):
        encoded = self.encode(decoded, **kwargs)
        return self.msg_obj(encoded, decoded=decoded, **kwargs)

    def decode(self, encoded: bytes, **kwargs) -> Sequence:
        yield [encoded, encoded]

    def encode(self, decoded, **kwargs):
        return decoded
