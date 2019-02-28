import datetime
from pycrate_core.charpy import Charpy

from lib.protocols.base import BaseProtocol
from lib.utils import cached_property, adapt_asn_domain, asn_timestamp_to_datetime

from typing import Sequence


class BasePyCrateAsnProtocol(BaseProtocol):

    """
    Manage ASN.1 messages via pycrate library
    """

    pycrate_asn_class = None

    def get_event_type(self):
        return ''

    @classmethod
    def decode_one(cls, encoded: bytes, log=None):
        return cls.decode(encoded, log=log)[0][0]

    @classmethod
    def decode(cls, encoded: bytes, log=None) -> Sequence:
        msgs = []
        char = Charpy(encoded)
        while char._cur < char._len_bit:
            start = int(char._cur / 8)
            cls.pycrate_asn_class.from_ber(char, single=True)
            end = int(char._cur / 8)
            msgs.append((encoded[start:end], cls.pycrate_asn_class()))
        return msgs

    @classmethod
    def encode(cls, decoded, log=None) -> bytes:
        return cls.pycrate_asn_class.to_ber(decoded)

    @cached_property
    def domain(self) -> str:
        return adapt_asn_domain(self.get_asn_domain())

    def get_timestamp(self) -> tuple:
        return ()

    @cached_property
    def timestamp(self):
        if self._timestamp:
            return self._timestamp
        timestamp = self.get_timestamp()
        if timestamp:
            return asn_timestamp_to_datetime(self.get_timestamp())
        return datetime.datetime.now()

    def get_asn_domain(self) -> tuple:
        raise NotImplementedError
