import datetime
from pycrate_core.charpy import Charpy

from lib.formats.base import BaseCodec, BaseMessageObject
from lib.utils import adapt_asn_domain, asn_timestamp_to_datetime

from typing import Sequence


class PyCrateAsnCodec(BaseCodec):

    """
    Decode & Encode ASN.1 messages via pycrate library
    """

    def __init__(self, *args, pycrate_asn_class, **kwargs):
        super().__init__(*args, **kwargs)
        self.pycrate_asn_class = pycrate_asn_class

    def decode(self, encoded: bytes, **kwargs) -> Sequence:
        char = Charpy(encoded)
        while char._cur < char._len_bit:
            start = int(char._cur / 8)
            self.pycrate_asn_class.from_ber(char, single=True)
            end = int(char._cur / 8)
            yield (encoded[start:end], self.pycrate_asn_class())

    def encode(self, decoded, **kwargs):
        return self.pycrate_asn_class.to_ber(decoded)


class BaseAsnObject(BaseMessageObject):
    codec_cls = PyCrateAsnCodec
    pycrate_asn_class = None

    @classmethod
    def get_codec_args(cls):
        return cls.pycrate_asn_class,

    def get_event_type(self):
        return ''

    @property
    def domain(self) -> str:
        return adapt_asn_domain(self.get_asn_domain())

    def get_timestamp(self) -> tuple:
        return ()

    @property
    def timestamp(self):
        timestamp = self.get_timestamp()
        if timestamp:
            return asn_timestamp_to_datetime(self.get_timestamp())
        if self.received_timestamp:
            return self.received_timestamp
        return datetime.datetime.now()

    def get_asn_domain(self) -> tuple:
        raise NotImplementedError
