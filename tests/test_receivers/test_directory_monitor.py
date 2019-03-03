import asyncio
import binascii
from pathlib import Path


from .base import BaseReceiverTestCase


class BaseDirectoryMonitorTestCase(BaseReceiverTestCase):

    async def send_one(self):
        msg = binascii.unhexlify(self.messages[0])
        path = Path(self.base_data_dir).joinpath('tmp/msg_0')
        path.write_bytes(msg)
        await asyncio.sleep(0.01)

    async def send_multiple_messages(self):
        for i, msg in enumerate(self.messages):
            path = Path(self.base_data_dir).joinpath('tmp/msg_%s' % i)
            path.write_bytes(binascii.unhexlify(msg))


class TestDirectoryMonitor(BaseDirectoryMonitorTestCase):
    config_file = 'directory_monitor_test_setup.ini'

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP', '00000001.TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)


class TestDirectoryMonitorBufferedFileStorage(BaseDirectoryMonitorTestCase):
    config_file = 'directory_monitor_buffered_storage_test_setup.ini'

    def test_00_one_msg(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        self.assertSendOneMsgOk(expected_file)

    def test_01_multiple(self):
        expected_file = Path(self.base_data_dir, 'Encoded', 'TCAP_MAP')
        directory = Path(self.base_data_dir, 'Encoded')
        self.assertMultipleMessagesSameSenderOK(expected_file, directory)
