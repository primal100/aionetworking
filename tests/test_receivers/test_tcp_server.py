import logging
from pathlib import Path
import multiprocessing

from lib import settings

from .base import BaseReceiverTestCase

logger = logging.getLogger(settings.LOGGER_NAME)


class TestTCPServer(BaseReceiverTestCase):
    status_change = multiprocessing.Event()
    stop_ordered = multiprocessing.Event()

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)

    def test_01_from_three_clients(self):
        expected_file1 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        expected_file2 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2_840001ff.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendFromThreeClientsOk(expected_file1, expected_file2, directory)

    """
    def test_send_incrementing_bytes(self):
        asyncio.run(tasks.send_incremented_msgs(self.client))

    def test_send_repeated_msg(self):
        asyncio.run(tasks.send_repeated_msg(self.client, self.multiple_encoded_hex[0]))

    def test_send_multiple_in_one(self):
        asyncio.run(tasks.send_hex(self.client, self.long_msg))
        time.sleep(100)

    def test_02_manage_100_messages(self):
        msgs = [self.multiple_encoded_hex[0] for i in range(0, 100)]
        asyncio.run(tasks.send_hex_msgs(self.client, msgs))
        #time.sleep(5)
        path = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        while len(list(path.iterdir())) < 100:
            logger.debug(len(list(path.iterdir())))
            time.sleep(0.003)
        files = list(path.iterdir())
        self.assertEqual(len(files), 100)
        time.sleep(1)

    def test_02_manage_multiple_messages(self):
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
"""


class TestTCPServerBufferedFileStorage(BaseReceiverTestCase):
    config_file = 'tcp_server_buffered_storage_test_setup.ini'
    status_change = multiprocessing.Event()
    stop_ordered = multiprocessing.Event()

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)

    def test_01_from_three_clients(self):
        expected_file1 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        expected_file2 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendFromThreeClientsOk(expected_file1, expected_file2, directory)

    def test_02_multiple_from_same_client(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertMultipleMessagesSameSenderOK(expected_file, directory)
