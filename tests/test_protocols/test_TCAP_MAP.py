import binascii
import datetime

from lib.basetestcase import BaseTestCase
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol


class TCAP_MAP_Testcase(BaseTestCase):
    protocol = TCAP_MAP_ASNProtocol
    sender = "10.10.10.10"
    encoded_hex = '62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0'

    def setUp(self):
        encoded = binascii.unhexlify(self.encoded_hex)
        self.interface = self.protocol(self.sender, encoded)

    def test_00_decoded(self):
        self.assertTupleEqual(self.interface.decoded, ('begin', {'otid': b'\x00\x00\x00\x01', 'dialoguePortion': {
            'direct-reference': (0, 0, 17, 773, 1, 1, 1), 'encoding': ('single-ASN1-type', ('DialoguePDU', (
            'dialogueRequest', {'protocol-version': (1, 1), 'application-context-name': (0, 4, 0, 0, 1, 0, 20, 2)})))},
                                                                'components': [('basicROS', ('invoke', {
                                                                    'invokeId': ('present', -1),
                                                                    'opcode': ('local', 45), 'argument': (
                                                                    'RoutingInfoForSM-Arg',
                                                                    {'msisdn': b'\x91\x14\x97Bu3\xf3',
                                                                     'sm-RP-PRI': False,
                                                                     'serviceCentreAddress': b'\x91\x14\x97yy\x08\xf0'})}))]}))

    def test_01_event_type(self):
        result = self.interface.get_event_type()
        self.assertEqual(result, 'begin')

    def test_02_prettified(self):
        self.assertListEqual(self.interface.prettified,
                             [{'event_type': 'begin', 'otid': '00000001', 'direct-reference': '0.0.17.773.1.1.1'}])

    def test_03_interface_name(self):
        result = self.interface.get_protocol_name()
        self.assertEqual(result, 'TCAP_MAP')

    def test_04_storage_path(self):
        result = self.interface.storage_path
        self.assertEqual(str(result), 'TCAP_MAP')

    def test_05_file_extension(self):
        result = self.interface.file_extension
        self.assertEqual(str(result), 'TCAPMAP')

    def test_07_storage_path_single(self):
        result = self.interface.storage_path_single
        self.assertEqual(str(result), 'TCAP_MAP')

    def test_08_storage_path_multiple(self):
        result = self.interface.storage_path_multiple
        self.assertEqual(str(result), 'TCAP_MAP')

    def test_09_storage_filename_single(self):
        result = self.interface.storage_filename_single
        self.assertEqual(str(result), '10.10.10.10_00000001.TCAPMAP')

    def test_10_storage_filename_multiple(self):
        result = self.interface.storage_filename_multiple
        self.assertEqual(str(result), '10.10.10.10_TCAP_MAP.TCAPMAPMULTI')

    def test_11_summaries(self):
        result = self.interface.summaries
        self.assertListEqual(result, [('begin', '00000001', self.interface.timestamp)])
        self.assertIsInstance(self.interface.summaries[0][2], datetime.datetime)
