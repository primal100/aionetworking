from lib.basetestcase import BaseTestCase
from lib.messagemanagers import BatchMessageManager, MessageFromNotAuthorizedHost
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface
from lib.actions import binary, decode, prettify, summarise
from lib import utils
import asyncio
import binascii
import shutil
import os


class TestMessageManager(BaseTestCase):
    sender = '10.10.10.10'
    interface = TCAP_MAP_ASNInterface
    multiple_encoded_hex = (
        '62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        '6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        '65164804a50500014904840001ff6c08a106020102020138',
        '643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )

    def setUp(self):

        try:
            shutil.rmtree(os.path.join(self.base_home))
        except OSError:
            pass

        action_modules = [binary, decode, prettify, summarise]
        print_modules = [summarise]
        self.loop = asyncio.get_event_loop()

        config = {
            'allowed_senders': (self.sender,),
        }
        action_config = {
            'home': self.base_home
        }
        aliases = {
            self.sender: 'Primary'
        }
        self.msgs = [binascii.unhexlify(encoded_hex) for encoded_hex in self.multiple_encoded_hex]
        self.manager = BatchMessageManager('PyMessageTest', self.interface, action_modules, print_modules, config,
                                      {}, action_config, aliases=aliases, loop=self.loop)

    def test_01_allowed_sender(self):
        host = self.manager.check_sender('10.10.10.10')
        self.assertEqual(host, 'Primary')

    def test_02_not_allowed_sender(self):
        self.assertRaises(MessageFromNotAuthorizedHost, self.manager.check_sender, '10.10.10.11')

    def test_03_manage_message(self):
        self.loop.run_until_complete(utils.run_wait_close(self.manager.manage_message, self.manager, '10.10.10.10', self.msgs[0]))
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

    def test_04_manage_multiple_messages(self):
        self.loop.run_until_complete(
            utils.run_wait_close_multiple(self.manager.manage_message, self.manager, '10.10.10.10', self.msgs))
        expected_file = os.path.join(self.base_home, 'Encoded', 'TCAP_MAP', 'Primary_00000000.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[3]))
        expected_file = os.path.join(self.base_home, 'Encoded', 'TCAP_MAP', 'Primary_00000001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[0]))
        expected_file = os.path.join(self.base_home, 'Encoded', 'TCAP_MAP', 'Primary_840001ff.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[1]))
        expected_file = os.path.join(self.base_home, 'Encoded', 'TCAP_MAP', 'Primary_a5050001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[2]))
        self.assertEqual(len(os.listdir(os.path.join(self.base_home, 'Decoded', 'TCAP_MAP'))), 4)
        self.assertEqual(len(os.listdir(os.path.join(self.base_home, 'Prettified', 'TCAP_MAP'))), 4)
        expected_file = os.path.join(self.base_home, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertPathExists(expected_file)
        with open(expected_file, 'r') as f:
            for i, l in enumerate(f):
                pass
        self.assertEqual(i + 1, 4)
