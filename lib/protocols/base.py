import asyncio
import datetime
import logging
from pathlib import Path
from pprint import pformat

from lib.utils import cached_property
from lib import settings

from typing import Sequence


logger = settings.get_logger('main')


class BaseProtocol:
    protocol_type = None
    protocol_name = ""
    binary = True
    configurable = {}
    supports_responses = False

    @classmethod
    def invalid_request_response(cls, sender, data, exc):
        return None

    @classmethod
    async def read_file(cls, file_path: Path):
        read_mode = 'rb' if cls.binary else 'r'
        async with settings.FILE_OPENER(file_path, read_mode) as f:
            return await f.read()

    @classmethod
    async def from_file(cls, file_path: Path, sender=''):
        logger.debug('Creating new %s message from %s', cls.protocol_name, file_path)
        encoded = await asyncio.create_task(cls.read_file(file_path))
        return cls.from_buffer(sender, encoded)

    @classmethod
    def from_buffer(cls, sender, encoded, **kwargs) -> Sequence:
        return [cls(sender, encoded, decoded, **kwargs) for decoded in cls.decode(encoded)]

    @classmethod
    def from_decoded(cls, decoded, sender='', **kwargs):
        return cls(sender, cls.encode(decoded), decoded, **kwargs)

    @classmethod
    def set_config(cls, **kwargs):
        config = settings.CONFIG.section_as_dict('Protocol', **cls.configurable)
        logger.debug('Found configuration for %s: %s', cls.protocol_name, config)
        config.update(kwargs)
        cls.config = config

    def __init__(self, sender, encoded, decoded, timestamp=None):
        self.sender = sender
        self._timestamp = timestamp
        self.encoded = encoded
        self.decoded = decoded

    def get_protocol_name(self) -> str:
        return self.protocol_name

    @cached_property
    def uid(self):
        return ''

    @property
    def pformat(self) -> str:
        return pformat(self.decoded)

    @classmethod
    def decode(cls, encoded: bytes) -> Sequence:
        return [encoded]

    @classmethod
    def encode(cls, decoded):
        return decoded

    @cached_property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp or datetime.datetime.now()

    def filter(self):
        return False

    def filter_by_action(self, action, to_print: bool):
        return False

    def make_response(self, *tasks): ...

    def make_response_invalid_request(self, task):
        return self.make_response(task)

    def __str__(self):
        return "%s message %s" % (self.protocol_name, id(self))
