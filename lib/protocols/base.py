import asyncio
import datetime
import logging
from pathlib import Path
from pprint import pformat

from lib.utils import cached_property
from lib import settings

from typing import Sequence


root_logger = logging.getLogger('root')


class BaseProtocol:
    protocol_type = None
    protocol_name = ""
    binary = True
    configurable = {}
    supports_responses = False

    @classmethod
    async def read_file(cls, file_path: Path, logger=root_logger):
        read_mode = 'rb' if cls.binary else 'r'
        async with settings.FILE_OPENER(file_path, read_mode) as f:
            return await f.read()

    @classmethod
    async def from_file(cls, file_path: Path, sender='', log=root_logger, **kwargs):
        log.debug('Creating new %s message from %s', cls.protocol_name, file_path)
        encoded = await asyncio.create_task(cls.read_file(file_path, logger=log))
        return cls.from_buffer(sender, encoded, log=log, **kwargs)

    @classmethod
    def from_buffer(cls, sender, encoded, log=root_logger, **kwargs) -> Sequence:
        return [cls(sender, encoded, decoded, log=log, **kwargs) for encoded, decoded in cls.decode(encoded, log=log)]

    @classmethod
    def from_decoded(cls, decoded, sender='', log=root_logger, **kwargs):
        return cls(sender, cls.encode(decoded, log=log), decoded, log=log, **kwargs)

    @classmethod
    def decode(cls, encoded: bytes, log=root_logger) -> Sequence:
        return [encoded, encoded]

    @classmethod
    def encode(cls, decoded, log=root_logger):
        return decoded

    def __init__(self, sender, encoded, decoded=None, timestamp=None, log=root_logger):
        self.sender = sender
        self.encoded = encoded
        self.decoded = decoded
        self.log = log
        self.received_timestamp = timestamp
        if not self.received_timestamp:
            self.received_timestamp = datetime.datetime.now()

    def get_protocol_name(self) -> str:
        return self.protocol_name

    @cached_property
    def uid(self):
        return ''

    @property
    def pformat(self) -> str:
        return pformat(self.decoded)

    @cached_property
    def timestamp(self) -> datetime.datetime:
        return self.received_timestamp

    def filter(self):
        return False

    def filter_by_action(self, action, to_print: bool):
        return False

    def make_response(self, *tasks): ...

    def make_response_invalid_request(self, task):
        return self.make_response(task)

    def __str__(self):
        return "%s message %s" % (self.protocol_name, id(self))


class BufferProtocol(BaseProtocol):
    pass
