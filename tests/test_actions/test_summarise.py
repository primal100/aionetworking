import datetime
from pathlib import Path
from unittest import skip
import asyncio

from lib.actions import summarise
from lib import utils
from .base import BaseTCAPMAPActionTestCase


class TestSummariseActionTCAPMAP(BaseTCAPMAPActionTestCase):
    action_cls = summarise.Action

    def test_00_content(self):
        content = self.action.get_content(self.msg)
        self.assertEqual(content,
                         "begin\t00000001\t2018-01-01 01:01:00\n"
                         )

    def test_01_print_msg(self):
        content = self.action.print_msg(self.msg)
        self.assertEqual(content,
                         'begin\t00000001\t2018-01-01 01:01:00'
                         )

    def test_02_print(self):
        for msg in self.msgs:
            self.action.print(msg)

    def test_03_get_extension(self):
        result = self.action.get_file_extension(self.msg)
        self.assertEqual(result, 'csv')

    def test_04_get_extension_multi(self):
        result = self.action.get_multi_file_extension(self.msg)
        self.assertEqual(result, 'csv')

    @skip
    def test_05_writes_for_store_many(self):
        content = self.action.writes_for_store_many(self.msgs)
        self.assertDictEqual(content,
                             {Path('10.10.10.10_TCAP_MAP.csv'): [('begin', '00000001', datetime.datetime(2018, 1, 1, 1, 1)), (
                             'continue', '840001ff', datetime.datetime(2018, 1, 1, 1, 1)), (
                                                           'continue', 'a5050001', datetime.datetime(2018, 1, 1, 1, 1)),
                                                           ('end', '00000000',
                                                            datetime.datetime(2018, 1, 1, 1, 1))]}
                         )

    def test_06_do(self):
        asyncio.run(self.do_async(self.action.do, self.msg))
        expected_file = Path(self.base_data_dir, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertFileContentsEqual(expected_file,
                                     'begin\t00000001\t2018-01-01 01:01:00\n'
                                     )

    @skip
    def test_07_do_many(self):
        self.action.do_multiple(self.msgs)
        expected_file = Path(self.base_data_dir, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertFileContentsEqual(expected_file,
                                     """begin	00000001	2018-01-01 01:01:00
continue	840001ff	2018-01-01 01:01:00
continue	a5050001	2018-01-01 01:01:00
end	00000000	2018-01-01 01:01:00
"""
                                     )

