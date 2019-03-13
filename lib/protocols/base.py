import asyncio
import datetime
import logging
from pathlib import Path
from pprint import pformat

from lib import settings

from typing import Sequence


class BaseCodec:
    configurable = {}
    codec_name = ''
    read_mode = 'rb'
    write_mode = 'wb'
    append_mode = 'ab'
    logger_name = 'receiver'

    def __init__(self, msg_obj, logger=None):
        self.msg_obj = msg_obj
        self.logger = logger or logging.getLogger(self.logger_name)

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

    def decode(self, encoded: bytes) -> Sequence:
        yield [encoded, encoded]

    def encode(self, decoded):
        return decoded


class EmbeddedDict(dict):
    def __getattr__(self, item):
        return self.get(item, None)


class BaseMessageObject:
    message_type = None
    codec_name = ""
    binary = True
    configurable = {}
    supports_responses = False
    codec_cls = BaseCodec
    codec_args = ()
    logger_name = 'receiver'

    @classmethod
    def get_codec(cls, **kwargs):
        return cls.codec_cls(cls, *cls.codec_args, **kwargs)

    def __init__(self, encoded, decoded=None, timestamp=None, logger=None, context=None):
        self.encoded = encoded
        self.decoded = decoded
        self.context = context or {}
        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger(self.logger_name)
        self.received_timestamp = timestamp
        if not self.received_timestamp:
            self.received_timestamp = datetime.datetime.now()

    def __getattr__(self, item):
        val = self.encoded.get(item, None)
        if isinstance(val, dict):
            return EmbeddedDict(val)
        return val

    @property
    def uid(self):
        return ''

    @property
    def pformat(self) -> str:
        return pformat(self.decoded)

    @property
    def timestamp(self) -> datetime.datetime:
        return self.received_timestamp

    def filter(self):
        return False

    def make_response(self, result): ...

    def make_response_on_exception(self, exception): ...

    def __str__(self):
        return "%s message %s" % (self.message_type, id(self))


class BufferObject(BaseMessageObject):
    pass
