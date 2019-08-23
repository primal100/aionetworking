from __future__ import annotations
import datetime
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
from pycrate_core.charpy import Charpy

from lib.formats.base import BaseCodec, BaseMessageObject
from lib.utils import adapt_asn_domain, asn_timestamp_to_datetime

from typing import AnyStr, Any, Type, Dict
from typing_extensions import Protocol


class ASNProtocol(Protocol):
    @classmethod
    def from_ber(cls, char, single: bool = False) -> Any: ...

    @classmethod
    def to_ber(cls, decoded: AnyStr) -> AnyStr: ...


executor = ProcessPoolExecutor()


@dataclass
class PyCrateAsnCodec(BaseCodec):

    """
    Decode & Encode ASN.1 messages via pycrate library
    """
    asn_class: Type[ASNProtocol] = None

    def decode(self, encoded: bytes, **kwargs):
        char = Charpy(encoded)
        while char._cur < char._len_bit:
            start = int(char._cur / 8)
            self.asn_class.from_ber(char, single=True)
            end = int(char._cur / 8)
            yield (encoded[start:end], self.asn_class())

    def encode(self, decoded, **kwargs) -> AnyStr:
        return self.asn_class.to_ber(decoded)


class BaseAsnObject(BaseMessageObject, Protocol):
    name = 'ASN.1'
    codec_cls = PyCrateAsnCodec
    asn_class = None

    @classmethod
    def _get_codec_kwargs(cls) -> Dict[str, Any]:
        return {'asn_class': cls.asn_class}

    @property
    def event_type(self) -> str:
        return ''

    @property
    def domain(self) -> str:
        return adapt_asn_domain(self._get_asn_domain())

    def _get_timestamp(self) -> tuple:
        return ()

    @property
    def timestamp(self) -> datetime:
        timestamp = self._get_timestamp()
        if timestamp:
            return asn_timestamp_to_datetime(self._get_timestamp())
        if self.received_timestamp:
            return self.received_timestamp
        return datetime.datetime.now()

    def _get_asn_domain(self) -> tuple:
        raise NotImplementedError
