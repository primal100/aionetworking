from lib.basetestcase import BaseTestCase
from datetime import datetime
import binascii
import os
import shutil

from lib.actions import prettify
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface


class TestPrettifyActionTCAPMAP(BaseTestCase):
    encoded_hex = '62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0'
    multiple_encoded_hex = (
        '62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        '6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        '65164804a50500014904840001ff6c08a106020102020138',
        '643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    action_module = prettify
    interface = TCAP_MAP_ASNInterface
    sender = '10.10.10.10'

    def setUp(self):
        try:
            shutil.rmtree(os.path.join(self.base_home, 'Prettified'))
        except OSError:
            pass
        timestamp = datetime(2018, 1, 1, 1, 1, 0)
        self.action = self.action_module.Action(self.base_home)
        self.msg = self.interface(self.sender, binascii.unhexlify(self.encoded_hex), timestamp=timestamp)
        self.msgs = [self.interface(self.sender, binascii.unhexlify(encoded_hex), timestamp=timestamp)
                     for encoded_hex in self.multiple_encoded_hex]

    def test_00_content(self):
        content = self.action.get_content(self.msg)
        self.assertEqual(content,
                         'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\n')

    def test_01_print_msg(self):
        content = self.action.print_msg(self.msg)
        self.assertEqual(content,
                         '\033[1mEvent_type\033[0m: begin\n\033[1mOtid\033[0m: 00000001\n\033[1mDirect-reference\033[0m: 0.0.17.773.1.1.1\n\033[1mTimestamp\033[0m: 2018-01-01 01:01:00\n\n')

    def test_02_print(self):
        self.action.print(self.msg)

    def test_03_get_extension(self):
        result = self.action.get_file_extension(self.msg)
        self.assertEqual(result, 'txt')

    def test_04_get_extension_multi(self):
        result = self.action.get_multi_file_extension(self.msg)
        self.assertEqual(result, 'txt')

    def test_05_writes_for_store_many(self):
        result = self.action.writes_for_store_many(self.msgs)
        self.assertDictEqual(result,
                             {
                                 '10.10.10.10_TCAP_MAP.txt': 'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\nEvent_type: continue\nOtid: 840001ff\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\nEvent_type: continue\nOtid: a5050001\nDirect-reference: \nTimestamp: 2018-01-01 01:01:00\n\nEvent_type: end\nOtid: 00000000\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\n'}
                             )

    def test_06_do(self):
        self.action.do(self.msg)
        expected_file = os.path.join(self.base_home, 'Prettified', 'TCAP_MAP', '10.10.10.10_00000001.txt')
        self.assertFileContentsEqual(expected_file,
                                     'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\n')

    def test_07_do_many(self):
        self.action.do_multiple(self.msgs)
        expected_file = os.path.join(self.base_home, 'Prettified', '10.10.10.10_TCAP_MAP.txt')
        self.assertFileContentsEqual(expected_file,
                                     'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\nEvent_type: continue\nOtid: 840001ff\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\nEvent_type: continue\nOtid: a5050001\nDirect-reference: \nTimestamp: 2018-01-01 01:01:00\n\nEvent_type: end\nOtid: 00000000\nDirect-reference: 0.0.17.773.1.1.1\nTimestamp: 2018-01-01 01:01:00\n\n'
                                     )

