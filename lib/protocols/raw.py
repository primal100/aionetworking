from .base import BaseProtocol
from lib.utils import timestamp_to_utc_string


class RawDataProtocol(BaseProtocol):
    protocol_name = 'rawdata'

    @property
    def storage_filename_single(self):
        return "%s_%s" % (self.sender, timestamp_to_utc_string(self.timestamp))

    @property
    def prettified(self):
        raise NotImplementedError

    @property
    def summaries(self):
        raise NotImplementedError
