from lib.basetestcase import BaseTestCase
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface
from lib.senders.asyncio_clients import TCPClient
import asyncio
import os
import subprocess
import definitions


class TestTCPServer(BaseTestCase):

    config_path = os.path.join(definitions.TEST_CONF_DIR, 'tcp_server')
    script_path = 'python run_binary.py'
    host = '127.0.0.1'
    port = 4001

    def setUp(self):
        os.chdir(definitions.SCRIPTS_DIR)
        cmd = '%s -c %s' % (self.script_path, self.config_path)
        print(cmd)
        subprocess.Popen(cmd)
        self.loop = asyncio.get_event_loop()
        self.client = TCPClient(TCAP_MAP_ASNInterface, self.host, self.port, loop=self.loop)

    def test_01_send(self):
        self.loop.run_until_complete(self.client.encode_and_send_msg(('begin', {'otid': b'\x00\x00\x00\x01', 'dialoguePortion': {
            'direct-reference': (0, 0, 17, 773, 1, 1, 1), 'encoding': ('single-ASN1-type', ('DialoguePDU', (
            'dialogueRequest', {'protocol-version': (1, 1), 'application-context-name': (0, 4, 0, 0, 1, 0, 20, 2)})))},
                                                                'components': [('basicROS', ('invoke', {
                                                                    'invokeId': ('present', -1),
                                                                    'opcode': ('local', 45), 'argument': (
                                                                    'RoutingInfoForSM-Arg',
                                                                    {'msisdn': b'\x91\x14\x97Bu3\xf3',
                                                                     'sm-RP-PRI': False,
                                                                     'serviceCentreAddress': b'\x91\x14\x97yy\x08\xf0'})}))]}))
                                     )
        expected_file = os.path.join(self.base_home, 'Encoded', 'TCAP_MAP', 'Primary_00000001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')

        expected_file = os.path.join(self.base_home, 'Decoded', 'TCAP_MAP', 'Primary_00000001.txt')
        self.assertFileContentsEqual(expected_file,
                                     "('begin',\n {'components': [('basicROS',\n                  ('invoke',\n                   {'argument': ('RoutingInfoForSM-Arg',\n                                 {'msisdn': b'\\x91\\x14\\x97Bu3\\xf3',\n                                  'serviceCentreAddress': b'\\x91\\x14\\x97y'\n                                                          b'y\\x08\\xf0',\n                                  'sm-RP-PRI': False}),\n                    'invokeId': ('present', -1),\n                    'opcode': ('local', 45)}))],\n  'dialoguePortion': {'direct-reference': (0, 0, 17, 773, 1, 1, 1),\n                      'encoding': ('single-ASN1-type',\n                                   ('DialoguePDU',\n                                    ('dialogueRequest',\n                                     {'application-context-name': (0,\n                                                                   4,\n                                                                   0,\n                                                                   0,\n                                                                   1,\n                                                                   0,\n                                                                   20,\n                                                                   2),\n                                      'protocol-version': (1, 1)})))},\n  'otid': b'\\x00\\x00\\x00\\x01'})")

        expected_file = os.path.join(self.base_home, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertPathExists(expected_file)
        expected_file = os.path.join(self.base_home, 'Prettified', 'TCAP_MAP', 'Primary_00000001.txt')
        self.assertPathExists(expected_file)


