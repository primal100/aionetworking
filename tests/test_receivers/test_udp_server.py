import logging
from pathlib import Path

from lib import settings

from .base import BaseReceiverTestCase

logger = logging.getLogger(settings.LOGGER_NAME)


class TestUDPServer(BaseReceiverTestCase):
    change_loop_policy = False
    config_file = 'udp_server_test_setup.ini'

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)

    def test_01_from_three_clients(self):
        expected_file1 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        expected_file2 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2_840001ff.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendFromThreeClientsOk(expected_file1, expected_file2, directory)


class TestUDPServerBufferedFileStorage(BaseReceiverTestCase):
    config_file = 'udp_server_buffered_storage_test_setup.ini'
    change_loop_policy = False

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
        self.assertMultipleMessagesSameSenderOK(expected_file, directory, delay=0.2)

    def test_03_play_recording(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        path = Path(settings.TESTS_DIR, 'recordings', 'localhost.recording')
        self.assertRecordingOK(path, expected_file, directory, delay=0.2)
