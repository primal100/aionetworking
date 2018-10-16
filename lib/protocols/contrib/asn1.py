from lib.protocols.base import BaseProtocol
from lib import utils
from lib.utils import cached_property

import datetime

class BasePyCrateAsnProtocol(BaseProtocol):

    """
    Manage ASN.1 messages via pycrate library
    """

    pycrate_asn_class = None
    supported_actions = ("binary", "decode", "prettify", "summaries")

    def get_event_type(self):
        return ''

    def decode(self):
        self.pycrate_asn_class.from_ber(self.encoded)
        decoded = self.pycrate_asn_class()
        return decoded

    def encode(self):
        return self.pycrate_asn_class.to_ber(self.decoded)

    @cached_property
    def domain(self):
        return utils.adapt_asn_domain(self.get_asn_domain())

    def get_timestamp(self):
        return ''

    @cached_property
    def timestamp(self):
        if self._timestamp:
            return self._timestamp
        timestamp = self.get_timestamp()
        if timestamp:
            return utils.asn_timestamp_to_datetime(self.get_timestamp())
        return datetime.datetime.now()

    @property
    def prettified(self):
        raise NotImplementedError

    def summaries(self):
        raise NotImplementedError

    def get_asn_domain(self):
        raise NotImplementedError
