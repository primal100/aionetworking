from pathlib import Path

from .base import BaseReceiverTestCase


class TestTCPServer(BaseReceiverTestCase):
    config_file = 'ssl_server_test_setup.ini'

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)

    def test_01_from_three_clients(self):
        expected_file1 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        expected_file2 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2_840001ff.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendFromThreeClientsOk(expected_file1, expected_file2, directory)


class TestTCPServerBufferedFileStorage(BaseReceiverTestCase):
    config_file = 'ssl_server_buffered_storage_test_setup.ini'

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
