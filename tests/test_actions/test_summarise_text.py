from lib.basetestcase import BaseTestCase
import os
import shutil

from lib.actions import summarise
from lib import utils
from lib.interfaces.contrib.json_sample import JsonSampleInterface


class TestSummariseActionJSON(BaseTestCase):
    encoded_json = '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}'
    encoded_jsons = [
        '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}',
        '{"id": 1, "actions": [{"timestamp": 1537006775.033925, "operation": "modify", "object_id": 7777}, {"timestamp": 1537006792.641033, "operation": "add", "object_id": 7778}, {"timestamp": 1537006799.78229, "operation": "delete", "object_id": 7779}]}'
    ]

    action_module = summarise
    interface = JsonSampleInterface
    sender = '10.10.10.10'

    def setUp(self):
        try:
            shutil.rmtree(os.path.join(self.base_home, 'Summaries'))
        except OSError:
            pass
        self.action = self.action_module.Action(self.base_home)
        self.msg = self.interface(self.sender, self.encoded_json)
        self.msgs = [self.interface(self.sender, encoded_json) for encoded_json in self.encoded_jsons]

    def test_00_content(self):
        content = self.action.get_content(self.msg)
        self.assertListEqual(content,
                             [('2018-09-15 11:09:31.033925', 1234, 'Modify'),
                              ('2018-09-15 11:09:42.641033', 2222, 'Add'),
                              ('2018-09-15 11:09:58.782290', 173, 'Delete')]
                             )

    def test_01_print_msg(self):
        content = self.action.print_msg(self.msg)
        self.assertEqual(content,
                         """2018-09-15 11:09:31.033925	1234	Modify
2018-09-15 11:09:42.641033	2222	Add
2018-09-15 11:09:58.782290	173	Delete"""
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

    def test_05_writes_for_store_many(self):
        content = self.action.writes_for_store_many(self.msgs)
        self.assertDictEqual(content,
                             {'10.10.10.10_JsonLogHandler.csv':
                                     [('2018-09-15 11:09:31.033925', 1234, 'Modify'), ('2018-09-15 11:09:42.641033', 2222, 'Add'), ('2018-09-15 11:09:58.782290', 173, 'Delete'), ('2018-09-15 11:09:35.033925', 7777, 'Modify'), ('2018-09-15 11:09:52.641033', 7778, 'Add'), ('2018-09-15 11:09:59.782290', 7779, 'Delete')]
                              }
                         )

    def test_06_do(self):
        self.action.do(self.msg)
        expected_file = os.path.join(self.base_home, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertFileContentsEqual(expected_file,
"""2018-09-15 11:09:31.033925	1234	Modify
2018-09-15 11:09:42.641033	2222	Add
2018-09-15 11:09:58.782290	173	Delete
"""
)

    def test_07_do_many(self):
        self.action.do_multiple(self.msgs)
        expected_file = os.path.join(self.base_home, 'Summaries', "Summary_%s.csv" % utils.current_date())
        self.assertFileContentsEqual(expected_file,
                                     """2018-09-15 11:09:31.033925	1234	Modify
2018-09-15 11:09:42.641033	2222	Add
2018-09-15 11:09:58.782290	173	Delete
2018-09-15 11:09:35.033925	7777	Modify
2018-09-15 11:09:52.641033	7778	Add
2018-09-15 11:09:59.782290	7779	Delete
"""
                                     )

