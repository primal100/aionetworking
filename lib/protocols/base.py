import datetime
import logging
from lib.actions.base import BaseAction
from lib.utils import cached_property, unpack_variable_len_strings
from pathlib import Path
from typing import Sequence, Mapping
import definitions


logger = logging.getLogger(definitions.LOGGER_NAME)


class BaseProtocol:
    asn_class = None
    protocol_type = None
    domain_id_name = None
    protocol_name = ""
    supported_actions = ()
    binary = True
    configurable = {}

    @classmethod
    def from_file(cls, sender, file_path:Path):
        logger.debug('Creating new', cls.protocol_name, 'message from', file_path)
        read_mode = 'rb' if cls.binary else 'r'
        with file_path.open(read_mode) as f:
            encoded = f.read()
        return cls(sender, encoded)

    @classmethod
    def from_file_multi(cls, sender, file_path:Path):
        logger.debug('Creating new', cls.protocol_name, 'messages from', file_path)
        read_mode = 'rb' if cls.binary else 'r'
        with file_path.open(read_mode) as f:
            contents = f.read()
        if cls.binary:
            return [cls(sender, encoded) for encoded in unpack_variable_len_strings(contents)]
        return [cls(sender, encoded) for encoded in contents.split('\n') if encoded]

    @classmethod
    def set_config(cls, **kwargs):
        config = definitions.CONFIG.section_as_dict('Protocol', **cls.configurable)
        logger.debug('Found configuration for', cls.protocol_name, ':', config)
        config.update(kwargs)
        cls.config = config

    def __init__(self, sender, encoded=None, decoded=None, timestamp=None):
        self.sender = sender
        self._timestamp = timestamp
        if encoded:
            self.encoded = encoded
            self.decoded = decoded or self.decode()
        else:
            self.decoded = decoded
            self.encoded = self.encode()

    def get_protocol_name(self) -> str:
        return self.protocol_name

    @property
    def storage_path(self) -> str:
        return self.get_protocol_name()

    @property
    def storage_path_single(self) -> str:
        return self.storage_path

    @property
    def storage_path_multiple(self) -> str:
        return self.storage_path

    @cached_property
    def prefix(self) -> str:
        return self.sender

    @cached_property
    def storage_filename_single(self) -> Path:
        return Path('%s_%s' % (self.prefix, self.uid))

    @cached_property
    def file_extension(self) -> str:
        return self.protocol_name.replace('_', '').replace('-', '') or self.protocol_name.replace('_', '').replace('-',
                                                                                                                   '')

    @property
    def storage_filename_multiple(self) -> Path:
        return Path('%s_%s' % (self.prefix, self.protocol_name))

    def unique_filename(self, base_path: Path, extension: str) -> Path:
        base_file_path = base_path.joinpath(self.storage_filename_single)
        file_path = base_file_path.with_suffix("." + extension)
        i = 1
        while file_path.exists():
            logger.debug('File %s exists. Creating alternative name' % file_path)
            file_path = base_file_path.with_suffix("_i." + extension)
            i += 1
        return file_path

    @cached_property
    def uid(self):
        return ''

    def pprinted(self) -> List[dict]:
        return self.prettified

    def decode(self):
        return self.encoded

    def encode(self):
        return self.decoded

    @cached_property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp or datetime.datetime.now()

    @cached_property
    def prettified(self) -> Sequence[Mapping]:
        raise NotImplementedError

    def summaries(self) -> Sequence[Sequence]:
        raise NotImplementedError

    def filter(self):
        return False

    def filter_by_action(self, action: BaseAction, toprint: bool):
        return False
