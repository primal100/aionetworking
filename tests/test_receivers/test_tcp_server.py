import asyncio
import binascii
from pathlib import Path
import os
import definitions
import settings
import time
import shutil
import multiprocessing

from lib.basetestcase import BaseTestCase
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.senders import tasks
from lib import utils
from lib.run_sender import get_sender

settings.CONFIG_ARGS = settings.TEST_CONF_DIR.joinpath('tcp_server_test_setup.ini'),
definitions.PROTOCOLS = {'TCAP': TCAP_MAP_ASNProtocol}


class TestTCPServer(BaseTestCase):
    multiple_encoded_hex = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    status_change = multiprocessing.Event()
    stop_ordered = multiprocessing.Event()
    client = get_sender()

    @staticmethod
    def start_server(status_change, stop_ordered):
        settings.CONFIG_ARGS = settings.TEST_CONF_DIR.joinpath('tcp_server_test_setup.ini'),
        from lib.run_receiver import main
        from lib.utils import set_loop
        set_loop()
        asyncio.run(main(status_change=status_change, stop_ordered=stop_ordered), debug=True)

    def start_server_process(self):
        self.process = multiprocessing.Process(target=self.start_server,
                                               args=(self.status_change, self.stop_ordered))
        self.process.start()
        self.status_change.wait()

    def setUp(self):
        try:
            shutil.rmtree(self.base_data_dir)
        except OSError:
            pass
        self.start_server_process()

    def tearDown(self):
        if os.name == 'nt':
            self.status_change.clear()
            self.stop_ordered.set()
            self.status_change.wait()
            self.stop_ordered.clear()
        self.process.terminate()
        self.process.join()

    def test_00_one_msg(self):
        asyncio.run(tasks.encode_send_msgs(self.client, [('begin', {'otid': b'\x00\x00\x00\x01', 'dialoguePortion': {
            'direct-reference': (0, 0, 17, 773, 1, 1, 1), 'encoding': ('single-ASN1-type', ('DialoguePDU', (
            'dialogueRequest', {'protocol-version': (1, 1), 'application-context-name': (0, 4, 0, 0, 1, 0, 20, 2)})))},
                                                                'components': [('basicROS', ('invoke', {
                                                                    'invokeId': ('present', -1),
                                                                    'opcode': ('local', 45), 'argument': (
                                                                    'RoutingInfoForSM-Arg',
                                                                    {'msisdn': b'\x91\x14\x97Bu3\xf3',
                                                                     'sm-RP-PRI': False,
                                                                     'serviceCentreAddress': b'\x91\x14\x97yy\x08\xf0'})}))]})])
                                     )
        time.sleep(3)
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')

        expected_file = Path(self.base_data_dir, 'Decoded', 'TCAP_MAP', 'localhost_00000001.txt')
        self.assertFileContentsEqual(expected_file,
                                     "('begin',\n {'components': [('basicROS',\n                  ('invoke',\n                   {'argument': ('RoutingInfoForSM-Arg',\n                                 {'msisdn': b'\\x91\\x14\\x97Bu3\\xf3',\n                                  'serviceCentreAddress': b'\\x91\\x14\\x97y'\n                                                          b'y\\x08\\xf0',\n                                  'sm-RP-PRI': False}),\n                    'invokeId': ('present', -1),\n                    'opcode': ('local', 45)}))],\n  'dialoguePortion': {'direct-reference': (0, 0, 17, 773, 1, 1, 1),\n                      'encoding': ('single-ASN1-type',\n                                   ('DialoguePDU',\n                                    ('dialogueRequest',\n                                     {'application-context-name': (0,\n                                                                   4,\n                                                                   0,\n                                                                   0,\n                                                                   1,\n                                                                   0,\n                                                                   20,\n                                                                   2),\n                                      'protocol-version': (1, 1)})))},\n  'otid': b'\\x00\\x00\\x00\\x01'})")

        expected_file = Path(self.base_data_dir, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertTrue(expected_file.exists())
        expected_file = Path(self.base_data_dir, 'Prettified', 'TCAP_MAP', 'localhost_00000001.txt')
        self.assertTrue(expected_file.exists())
        expected_file = Path(self.base_data_dir, 'recordings', 'testrecord.mmr')
        self.assertTrue(expected_file.exists())

    def test_01_manage_100_messages(self):
        msgs = [self.multiple_encoded_hex[0] for i in range(0, 100)]
        asyncio.run(tasks.send_hex_msgs(self.client, msgs))
        time.sleep(3)
        path = os.path.join(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        files = os.listdir(path)
        self.assertEqual(len(files), 100)

    def test_01_manage_multiple_messages(self):
        asyncio.run(tasks.send_hex_msgs(self.client, self.multiple_encoded_hex))
        time.sleep(3)
        expected_file = os.path.join(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000000.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[3]))
        expected_file = os.path.join(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[0]))
        expected_file = os.path.join(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_840001ff.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[1]))
        expected_file = os.path.join(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_a5050001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file, binascii.unhexlify(self.multiple_encoded_hex[2]))
        self.assertEqual(len(os.listdir(os.path.join(self.base_data_dir, 'Decoded', 'TCAP_MAP'))), 4)
        self.assertEqual(len(os.listdir(os.path.join(self.base_data_dir, 'Prettified', 'TCAP_MAP'))), 4)
        expected_file = os.path.join(self.base_data_dir, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertPathExists(expected_file)
        with open(expected_file, 'r') as f:
            for i, l in enumerate(f):
                pass
        self.assertEqual(i + 1, 4)
        expected_file = os.path.join(definitions.TEST_DATA_DIR, 'recordings', 'testrecord.mmr')
        self.assertPathExists(expected_file)

    def test_02_play_recording(self):
        recording = os.path.join(definitions.TESTS_DIR, 'recordings', 'tcprecord.mmr')
        asyncio.run(tasks.play_recording(self.client, recording))
        time.sleep(3)
        expected_file = os.path.join(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAPMAP')
        self.assertBinaryFileContentsEqual(expected_file,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')

        expected_file = os.path.join(self.base_data_dir, 'Decoded', 'TCAP_MAP', 'localhost_00000001.txt')
        self.assertFileContentsEqual(expected_file,
                                     "('begin',\n {'components': [('basicROS',\n                  ('invoke',\n                   {'argument': ('RoutingInfoForSM-Arg',\n                                 {'msisdn': b'\\x91\\x14\\x97Bu3\\xf3',\n                                  'serviceCentreAddress': b'\\x91\\x14\\x97y'\n                                                          b'y\\x08\\xf0',\n                                  'sm-RP-PRI': False}),\n                    'invokeId': ('present', -1),\n                    'opcode': ('local', 45)}))],\n  'dialoguePortion': {'direct-reference': (0, 0, 17, 773, 1, 1, 1),\n                      'encoding': ('single-ASN1-type',\n                                   ('DialoguePDU',\n                                    ('dialogueRequest',\n                                     {'application-context-name': (0,\n                                                                   4,\n                                                                   0,\n                                                                   0,\n                                                                   1,\n                                                                   0,\n                                                                   20,\n                                                                   2),\n                                      'protocol-version': (1, 1)})))},\n  'otid': b'\\x00\\x00\\x00\\x01'})")

        expected_file = os.path.join(self.base_data_dir, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertPathExists(expected_file)
        expected_file = os.path.join(self.base_data_dir, 'Prettified', 'TCAP_MAP', 'localhost_00000001.txt')
        self.assertPathExists(expected_file)
        expected_file = os.path.join(definitions.TESTS_DIR, 'recordings', 'testrecord.mmr')
        self.assertPathExists(expected_file)

