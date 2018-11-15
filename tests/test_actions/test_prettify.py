import asyncio
from pathlib import Path
from unittest import skip

from lib.actions import prettify
from .base import BaseTCAPMAPActionTestCase


class TestPrettifyActionTCAPMAP(BaseTCAPMAPActionTestCase):
    action_cls = prettify.Action

    def test_00_content(self):
        content = self.action.get_content(self.msg)
        self.assertEqual(content,
                         'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\n\n')

    def test_01_print_msg(self):
        content = self.print_action.print_msg(self.msg)
        self.assertEqual(content,
                         '\033[1mEvent_type\033[0m: begin\n\033[1mOtid\033[0m: 00000001\n\033[1mDirect-reference\033[0m: 0.0.17.773.1.1.1\n\n')

    def test_02_print(self):
        self.print_action.print(self.msg)

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
                                 Path('10.10.10.10_TCAP_MAP.txt'): 'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\n\nEvent_type: continue\nOtid: 840001ff\nDirect-reference: 0.0.17.773.1.1.1\n\nEvent_type: continue\nOtid: a5050001\nDirect-reference: \n\nEvent_type: end\nOtid: 00000000\nDirect-reference: 0.0.17.773.1.1.1\n\n'}
                             )

    def test_06_do(self):
        asyncio.run(self.do_async(self.action.do, self.msg))
        expected_file = Path(self.base_data_dir, 'Prettified', 'TCAP_MAP', '10.10.10.10_00000001.txt')
        self.assertFileContentsEqual(expected_file,
                                     'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\n\n')

    @skip
    def test_07_do_many(self):
        self.action.do_multiple(self.msgs)
        expected_file = Path(self.base_data_dir, 'Prettified', '10.10.10.10_TCAP_MAP.txt')
        self.assertFileContentsEqual(expected_file,
                                     'Event_type: begin\nOtid: 00000001\nDirect-reference: 0.0.17.773.1.1.1\n\nEvent_type: continue\nOtid: 840001ff\nDirect-reference: 0.0.17.773.1.1.1\n\nEvent_type: continue\nOtid: a5050001\nDirect-reference: \n\nEvent_type: end\nOtid: 00000000\nDirect-reference: 0.0.17.773.1.1.1\n\n'
                                     )

