import datetime
import logging
from lib.protocols.base import BaseProtocol
from lib import utils, settings
from lib.utils import cached_property

from typing import Sequence, Mapping


from pycrate_core.charpy import Charpy

logger = logging.getLogger(settings.LOGGER_NAME)


class BasePyCrateAsnProtocol(BaseProtocol):

    """
    Manage ASN.1 messages via pycrate library
    """

    pycrate_asn_class = None
    supported_actions = ("binary", "decode", "prettify", "summarise")

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
        return utils.adapt_asn_domain(self.get_asn_domain())

    def get_timestamp(self) -> tuple:
        return ()

    @cached_property
    def timestamp(self):
        if self._timestamp:
            return self._timestamp
        timestamp = self.get_timestamp()
        if timestamp:
            return utils.asn_timestamp_to_datetime(self.get_timestamp())
        return datetime.datetime.now()

    @property
    def prettified(self) -> Sequence[Mapping]:
        raise NotImplementedError

    @property
    def summaries(self) -> Sequence[Sequence]:
        raise NotImplementedError

    def get_asn_domain(self) -> tuple:
        raise NotImplementedError
