import asyncio
import datetime
import logging
from pathlib import Path
from pprint import pformat

from lib import settings
from lib.utils import Record

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

    def set_logger(self, logger):
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


class EmbeddedDict(dict):
    def __getattr__(self, item):
        return self.get(item, None)

    def __getitem__(self, item):
        return self.__getattr__(item)


class MessageObject:
    def __new__(cls, name):
        from lib import definitions
        return definitions.DATA_FORMATS[name]


class BaseMessageObject:
    message_type = None
    codec_name = ""
    binary = True
    configurable = {}
    supports_responses = False
    codec_cls = BaseCodec
    logger_name = 'receiver'
    id_attr = 'id'

    @classmethod
    def get_codec(cls, **kwargs):
        return cls.codec_cls(cls, *cls.get_codec_args(), **kwargs)

    def __init__(self, encoded, decoded=None, timestamp=None, logger=None, context=None):
        self.encoded = encoded
        self.decoded = decoded
        self.context = context or {}
        if not logger:
            logger = logging.getLogger(self.logger_name)
        self.conn_logger = logger
        self.logger = logger.get_sibling('msg', extra={'msg_obj': self})
        self.received_timestamp = timestamp
        if not self.received_timestamp:
            self.received_timestamp = datetime.datetime.now()

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
    def timestamp(self) -> datetime.datetime:
        return self.received_timestamp

    def filter(self):
        return False

    def processed(self):
        if self.stats_logger:
            self.stats_logger.on_message_processed(self)

    def __str__(self):
        return "%s message %s" % (self.message_type, self.uid)


class BufferObject(BaseMessageObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._record = Record()

    @property
    def record(self):
        return self._record.pack_client_msg(self)
