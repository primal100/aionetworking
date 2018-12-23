import datetime
import logging
from pycrate_core.charpy import Charpy

from lib.protocols.base import BaseProtocol
from lib import settings
from lib.utils import cached_property, adapt_asn_domain, asn_timestamp_to_datetime

from typing import Sequence


logger = settings.get_logger('main')


class BasePyCrateAsnProtocol(BaseProtocol):

    """
    Manage ASN.1 messages via pycrate library
    """

    pycrate_asn_class = None

    def get_event_type(self):
        return ''

    @classmethod
    def decode(cls, encoded: bytes) -> Sequence:
        msgs = []
        char = Charpy(encoded)
        while char._cur < char._len_bit:
            cls.pycrate_asn_class.from_ber(char, single=True)
            msgs.append(cls.pycrate_asn_class())
        return msgs

    @classmethod
    def encode(cls, decoded) -> bytes:
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
