import datetime
import asyncio
import logging

from lib.utils import cached_property
import settings

from typing import TYPE_CHECKING, Sequence, Mapping
from pathlib import Path
if TYPE_CHECKING:
    from lib.actions.base import BaseRawAction
else:
    BaseRawAction = None

logger = logging.getLogger(settings.LOGGER_NAME)


class BaseProtocol:
    protocol_type = None
    protocol_name = ""
    supported_actions = ()
    binary = True
    configurable = {}
    supports_responses = False

    @classmethod
    def invalid_request_response(cls, sender, data, exc):
        return None

    @classmethod
    async def read_file(cls, file_path: Path):
        read_mode = 'rb' if cls.binary else 'r'
        async with settings.FILE_OPENER.open(file_path, read_mode) as f:
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

    @property
    def storage_path(self) -> Path:
        return Path(self.get_protocol_name())

    @property
    def storage_path_single(self) -> Path:
        return Path(self.storage_path)

    @property
    def storage_path_multiple(self) -> Path:
        return Path(self.storage_path)

    @cached_property
    def prefix(self) -> str:
        return self.sender

    @cached_property
    def storage_filename_single(self) -> Path:
        return Path('%s_%s.%s' % (self.prefix, self.uid, self.file_extension))

    @cached_property
    def storage_filename_multi(self) -> Path:
        return Path('%s_%s.%s' % (self.prefix, self.protocol_name, self.file_extension))

    @cached_property
    def file_extension(self) -> str:
        return self.protocol_name.replace('_', '').replace('-', '') or self.protocol_name.replace('_', '').replace('-',
                                                                                                                   '')

    @cached_property
    def uid(self):
        return ''

    def pprinted(self) -> Sequence[Mapping]:
        return self.prettified

    @classmethod
    def decode(cls, encoded: bytes) -> Sequence:
        return [encoded]

    def encode(self):
        return self.decoded

    @cached_property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp or datetime.datetime.now()

    @property
    def prettified(self) -> Sequence[Mapping]:
        raise NotImplementedError

    @property
    def summaries(self) -> Sequence[Mapping]:
        raise NotImplementedError

    def filter(self):
        return False

    def filter_by_action(self, action: BaseRawAction, to_print: bool):
        return False

    def make_response(self, *tasks): ...

    def make_response_invalid_request(self, task):
        return self.make_response(task)

