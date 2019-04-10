import binascii
from pycrate_asn1dir import TCAP_MAP
from lib.formats.contrib.asn1 import BaseAsnObject
from lib.utils import cached_property


class TCAPMAPASNObject(BaseAsnObject):

    pycrate_asn_class = TCAP_MAP.TCAP_MAP_Messages.TCAP_MAP_Message
    protocol_name = "TCAP_MAP"

    """
    Sample implementation of interface for ASN.1 messages via pycrate library
    """

    def get_event_type(self) -> str:
        return self.decoded[0]

    def get_asn_domain(self):
        if 'dialoguePortion' in self.decoded[1]:
            return self.decoded[1]['dialoguePortion']['direct-reference']
        else:
            return ''

    @cached_property
    def otid(self) -> bytes:
        if 'otid' in self.decoded[1]:
            return binascii.hexlify(self.decoded[1]['otid'])
        return binascii.hexlify(b'\x00\x00\x00\x00')

    @cached_property
    def uid(self):
        return self.otid.decode()
