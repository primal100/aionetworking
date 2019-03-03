import asyncio
from pathlib import Path

from .base import BaseReceiverTestCase
from lib import settings
from lib.utils import Record


class TestTCPServer(BaseReceiverTestCase):
    config_file = 'tcp_server_test_setup_record.ini'

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)
        expected_recording = Path(self.base_data_dir, 'Recordings', 'localhost.recording')
        recording = list(Record.from_file(expected_recording))[0]
        self.assertDictEqual(recording,
                    {'sent_by_server': False,
                    'seconds': 0,
                    'peer': 'localhost',
                    'data': b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0'
                                     })

    def test_01_from_three_clients(self):
        expected_file1 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        expected_file2 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2_840001ff.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendFromThreeClientsOk(expected_file1, expected_file2, directory)
        expected_recording1 = Path(self.base_data_dir, 'Recordings', 'localhost.recording')
        recording1 = list(Record.from_file(expected_recording1))[0]
        self.assertDictEqual(recording1,
                    {'sent_by_server': False,
                    'seconds': 0,
                    'peer': 'localhost',
                    'data': b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0'
                                     })
        expected_recording2 = Path(self.base_data_dir, 'Recordings', 'localhost2.recording')
        recording2 = list(Record.from_file(expected_recording2))[0]
        self.assertDictEqual(recording2,
                    {'sent_by_server': False,
                    'seconds': recording2['seconds'],
                    'peer': 'localhost2',
                    'data': b"e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00"
                                     })
        expected_recording3 = Path(self.base_data_dir, 'Recordings', 'localhost3.recording')
        self.assertFalse(expected_recording3.exists())


class TestTCPServerBufferedFileStorage(BaseReceiverTestCase):
    config_file = 'tcp_server_buffered_storage_test_setup_record.ini'

    def test_00_multiple_from_same_client(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertMultipleMessagesSameSenderOK(expected_file, directory)
        expected_recording = Path(self.base_data_dir, 'Recordings', 'localhost.recording')
        recording = list(Record.from_file(expected_recording))
        self.assertEqual(len(recording), 4)

    def test_01_play_recording(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        path = Path(settings.TESTS_DIR, 'recordings', 'localhost.recording')
        self.assertRecordingOK(expected_file, directory)
