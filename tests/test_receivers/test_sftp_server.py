import asyncio
import binascii
from pathlib import Path

from .base import BaseReceiverTestCase
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol


class BaseSFTPTestCase(BaseReceiverTestCase):

    def setUp(self):
        super(BaseSFTPTestCase, self).setUp()
        msgs = [TCAP_MAP_ASNProtocol.decode_one(binascii.unhexlify(msg)) for msg in self.messages]
        path = self.base_data_dir.joinpath('tmp')
        path.mkdir(parents=True, exist_ok=True)

    async def send_three_clients(self, msg1, msg2, msg3):
        client1 = self.get_sender(srcip='127.0.0.1')
        client2 = self.get_sender(srcip='127.0.0.2')
        client3 = self.get_sender(srcip='127.0.0.3')
        async with client1, client2:
            await client1.send_hex(msg1)
            await client2.send_hex(msg2)
        try:
            await client3.start()
            raise AssertionError('ConnectionResetError not raised by client3')
        except ConnectionResetError:
            pass
        await asyncio.sleep(3)


class TestSFTPServer(BaseSFTPTestCase):
    config_file = 'sftp_server_test_setup.ini'
    sender_kwargs = {'sftp_kwargs': {'username': 'sftpuser', 'password': 'abcd1234'}}

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)

    def test_01_from_three_clients(self):
        expected_file1 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost_00000001.TCAP_MAP')
        expected_file2 = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost2_840001ff.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendFromThreeClientsOk(expected_file1, expected_file2, directory)


class TestTCPServerBufferedFileStorage(BaseSFTPTestCase):
    config_file = 'sftp_server_buffered_storage_test_setup.ini'
    sender_kwargs = {'sftp_kwargs': {'username': 'sftpuser'}}

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

    def test_03_play_recording(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', 'localhost.TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertRecordingOK(expected_file, directory)
