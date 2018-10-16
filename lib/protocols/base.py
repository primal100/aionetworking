import os
import datetime
import logging
from lib.utils import cached_property, unpack_variable_len_strings


logger = logging.getLogger()


class BaseProtocol:
    asn_class = None
    protocol_type = None
    domain_id_name = None
    protocol_name = ""
    supported_actions = ()
    binary = True

    @classmethod
    def from_file(cls, sender, file_path, config=None):
        logger.debug('Creating new %s message from %s' % (cls.protocol_name, file_path))
        read_mode = 'rb' if cls.binary else 'r'
        with open(file_path, read_mode) as f:
            encoded = f.read()
        return cls(sender, encoded, config=config)

    @classmethod
    def from_file_multi(cls, sender, file_path, config=None):
        logger.debug('Creating new %s messages from %s' % (cls.protocol_name, file_path))
        read_mode = 'rb' if cls.binary else 'r'
        with open(file_path, read_mode) as f:
            contents = f.read()
        if cls.binary:
            return [cls(sender, encoded, config=config) for encoded in unpack_variable_len_strings(contents)]
        return [cls(sender, encoded, config=config) for encoded in contents.split('\n') if encoded]

    def __init__(self, sender, encoded=None, decoded=None, timestamp=None, config=None):
        self.sender = sender
        self.config = config or {}
        self._timestamp = timestamp
        if encoded:
            self.encoded = encoded
            self.decoded = decoded or self.decode()
        else:
            self.decoded = decoded
            self.encoded = self.encode()

    def get_protocol_name(self):
        return self.protocol_name

    @property
    def storage_path(self):
        return self.get_protocol_name()

    @property
    def storage_path_single(self):
        return self.storage_path

    @property
    def storage_path_multiple(self):
        return self.storage_path

    @cached_property
    def prefix(self):
        return self.sender

    @cached_property
    def storage_filename_single(self):
        return '%s_%s' % (self.prefix, self.uid)

    @cached_property
    def file_extension(self):
        return self.protocol_name.replace('_', '').replace('-', '') or self.protocol_name.replace('_', '').replace('-',
                                                                                                                   '')

    @property
    def storage_filename_multiple(self):
        return '%s_%s' % (self.prefix, self.protocol_name)

    def unique_filename(self, base_path, extension):
        os.makedirs(base_path, exist_ok=True)
        base_file_path = os.path.join(base_path, self.storage_filename_single)
        file_path = "%s.%s" % (base_file_path, extension)
        i = 1
        while os.path.exists(file_path):
            logger.debug('File %s exists. Creating alternative name' % (file_path))
            file_path = "%s_%s.%s" % (base_file_path, i, extension)
            i += 1
        return file_path

    @cached_property
    def uid(self):
        return ''

    def pprinted(self):
        return self.prettified

    def __str__(self):
        return self.pprinted()

    def decode(self):
        return self.encoded

    def encode(self):
        return self.decoded

    @cached_property
    def timestamp(self):
        return self._timestamp or datetime.datetime.now()

    @cached_property
    def prettified(self):
        raise NotImplementedError

    def summaries(self):
        raise NotImplementedError

    def filter(self):
        return False

    def filter_by_action(self, action, toprint):
        return False
