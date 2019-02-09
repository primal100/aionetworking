import asyncio
import binascii
import logging
from pathlib import Path
import os
import time
import shutil
import multiprocessing

from lib.basetestcase import BaseTestCase
from lib.senders import tasks
from lib import utils, definitions, settings
from lib.run_sender import get_sender

logger = logging.getLogger(settings.LOGGER_NAME)


class TestTCPServer(BaseTestCase):
    multiple_encoded_hex = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    long_msg = b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f06581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000'
    status_change = multiprocessing.Event()
    stop_ordered = multiprocessing.Event()

    @staticmethod
    def start_server(status_change, stop_ordered):
        settings.CONFIG_ARGS = settings.TEST_CONF_DIR.joinpath('tcp_server_test_setup.ini'),
        from lib.run_receiver import main
        from lib.utils import set_loop_policy
        set_loop_policy()
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
        self.status_change.clear()
        self.stop_ordered.set()
        self.status_change.wait()
        self.process.terminate()
        self.process.join()

    def test_00_one_msg(self):
        client = get_sender()
        asyncio.run(tasks.encode_send_msgs(client, [('begin', {'otid': b'\x00\x00\x00\x01', 'dialoguePortion': {
            'direct-reference': (0, 0, 17, 773, 1, 1, 1), 'encoding': ('single-ASN1-type', ('DialoguePDU', (
            'dialogueRequest', {'protocol-version': (1, 1), 'application-context-name': (0, 4, 0, 0, 1, 0, 20, 2)})))},
                                                                'components': [('basicROS', ('invoke', {
                                                                    'invokeId': ('present', -1),
                                                                    'opcode': ('local', 45), 'argument': (
                                                                    'RoutingInfoForSM-Arg',
                                                                    {'msisdn': b'\x91\x14\x97Bu3\xf3',
                                                                     'sm-RP-PRI': False,
                                                                     'serviceCentreAddress': b'\x91\x14\x97yy\x08\xf0'})}))]})]),
                                     debug=True)
        time.sleep(3)
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertBinaryFileContentsEqual(expected_file,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')

    @staticmethod
    async def send_three_clients(client1, client2, client3, msg1, msg2, msg3):
        async with client1, client2, client3:
            await client1.send_hex(msg1)
            await client2.send_hex(msg2)
            await client3.send_hex(msg3)
        await asyncio.sleep(3)

    def test_01_from_three_clients(self):
        client_one = get_sender(srcip='127.0.0.1')
        client_two = get_sender(srcip='127.0.0.2')
        client_three = get_sender(srcip='127.0.0.3')
        asyncio.run(self.send_three_clients(client_one, client_two, client_three, self.multiple_encoded_hex[0],
                                            self.multiple_encoded_hex[1], self.multiple_encoded_hex[2]))
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertBinaryFileContentsEqual(expected_file,
                                     b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0')
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2_840001ff.TCAP_MAP')
        self.assertBinaryFileContentsEqual(expected_file,
                                           b"e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00")
        self.assertNumberOfFilesInDirectory(Path(self.base_data_dir, 'Encoded', 'TCAP_MAP'), 2)

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
