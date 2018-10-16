from pycrate_asn1dir import TCAP_MAP
from lib.protocols.contrib.asn1 import BasePyCrateAsnProtocol
from lib.utils import cached_property

import binascii


class TCAP_MAP_ASNProtocol(BasePyCrateAsnProtocol):

    pycrate_asn_class = TCAP_MAP.TCAP_MAP_Messages.TCAP_MAP_Message
    protocol_name = "TCAP_MAP"

    """
    Sample implementation of interface for ASN.1 messages via pycrate library
    """

    def get_event_type(self):
        return self.decoded[0]

    def get_asn_domain(self):
        if 'dialoguePortion' in self.decoded[1]:
            return self.decoded[1]['dialoguePortion']['direct-reference']
        else:
            return ''

    @cached_property
    def otid(self):
        if 'otid' in self.decoded[1]:
            return binascii.hexlify(self.decoded[1]['otid'])
        return binascii.hexlify(b'\x00\x00\x00\x00')

    @cached_property
    def uid(self):
        return self.otid.decode()

    @cached_property
    def prettified(self):
        return [{
            'event_type': self.get_event_type(),
            'otid': self.uid,
            'direct-reference': self.domain,
        }]

    @cached_property
    def summaries(self):
        return [
            (self.get_event_type(), self.uid, self.timestamp)
        ]
