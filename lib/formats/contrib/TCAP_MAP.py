from __future__ import annotations
import binascii
from dataclasses import dataclass
try:
    from pycrate_asn1dir import TCAP_MAP
except ImportError:
    TCAP_MAP = 'tcapmap'
from lib.formats.contrib.asn1 import BaseAsnObject
from lib.compatibility import cached_property


@dataclass
class TCAPMAPASNObject(BaseAsnObject):

    asn_class = TCAP_MAP
    name = "TCAP_MAP"
    next_otid = 0x00000000

    """
    Sample implementation of interface for ASN.1 messages via pycrate library
    """

    def _get_asn_domain(self):
        if 'dialoguePortion' in self.decoded[1]:
            return self.decoded[1]['dialoguePortion']['direct-reference']
        else:
            return ''

    @property
    def event_type(self) -> str:
        return self.decoded[0]

    @cached_property
    def otid(self) -> bytes:
        if 'otid' in self.decoded[1]:
            return binascii.hexlify(self.decoded[1]['otid'])
        otid = self.__class__.next_otid
        self.__class__.next_otid += 1
        return format(otid, '08x').encode()

    @cached_property
    def uid(self) -> str:
        return self.otid.decode()
