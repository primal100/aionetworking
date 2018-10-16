from lib.basetestcase import BaseTestCase
import os
import shutil

from lib.actions import prettify
from lib.protocols.contrib.json_sample import JsonSampleProtocol


class TestPrettifyActionJSON(BaseTestCase):
    encoded_json = '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}'
    encoded_jsons = [
        '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}',
        '{"id": 1, "actions": [{"timestamp": 1537006775.033925, "operation": "modify", "object_id": 7777}, {"timestamp": 1537006792.641033, "operation": "add", "object_id": 7778}, {"timestamp": 1537006799.78229, "operation": "delete", "object_id": 7779}]}'
    ]
    action_module = prettify
    protocol = JsonSampleProtocol
    sender = '10.10.10.10'

    def setUp(self):
        try:
            shutil.rmtree(os.path.join(self.base_data_dir, 'Prettified'))
        except OSError:
            pass
        config = self.prepare_config()
        self.action = self.action_module.Action(self.base_data_dir, config)
        self.msg = self.protocol(self.sender, self.encoded_json)
        self.msgs = [self.protocol(self.sender, encoded_json) for encoded_json in self.encoded_jsons]

    def test_00_content(self):
        content = self.action.get_content(self.msg)
        self.assertEqual(content,
                         """Time: 2018-09-15 11:09:31.033925
Object_id: 1234
Operation: Modify

Time: 2018-09-15 11:09:42.641033
Object_id: 2222
Operation: Add

Time: 2018-09-15 11:09:58.782290
Object_id: 173
Operation: Delete

""")

    def test_01_print(self):
        self.action.print(self.msg)

    def test_02_get_extension(self):
        result = self.action.get_file_extension(self.msg)
        self.assertEqual(result, 'txt')

    def test_03_get_extension_multi(self):
        result = self.action.get_multi_file_extension(self.msg)
        self.assertEqual(result, 'txt')

    def test_04_writes_for_store_many(self):
        result = self.action.writes_for_store_many(self.msgs)
        self.assertDictEqual(result,
                             {'10.10.10.10_JsonLogHandler.txt':
                             """Time: 2018-09-15 11:09:31.033925
Object_id: 1234
Operation: Modify

Time: 2018-09-15 11:09:42.641033
Object_id: 2222
Operation: Add

Time: 2018-09-15 11:09:58.782290
Object_id: 173
Operation: Delete

Time: 2018-09-15 11:09:35.033925
Object_id: 7777
Operation: Modify

Time: 2018-09-15 11:09:52.641033
Object_id: 7778
Operation: Add

Time: 2018-09-15 11:09:59.782290
Object_id: 7779
Operation: Delete

"""})

    def test_05_do(self):
        self.action.do(self.msg)
        expected_file = os.path.join(self.base_data_dir, 'Prettified', 'JsonLogHandler', '10.10.10.10_0.txt')
        self.assertFileContentsEqual(expected_file,
                                     """Time: 2018-09-15 11:09:31.033925
Object_id: 1234
Operation: Modify

Time: 2018-09-15 11:09:42.641033
Object_id: 2222
Operation: Add

Time: 2018-09-15 11:09:58.782290
Object_id: 173
Operation: Delete

""")

    def test_06_do_many(self):
        self.action.do_multiple(self.msgs)
        expected_file = os.path.join(self.base_data_dir, 'Prettified', '10.10.10.10_JsonLogHandler.txt')
        self.assertFileContentsEqual(expected_file,
                                     """Time: 2018-09-15 11:09:31.033925
Object_id: 1234
Operation: Modify

Time: 2018-09-15 11:09:42.641033
Object_id: 2222
Operation: Add

Time: 2018-09-15 11:09:58.782290
Object_id: 173
Operation: Delete

Time: 2018-09-15 11:09:35.033925
Object_id: 7777
Operation: Modify

Time: 2018-09-15 11:09:52.641033
Object_id: 7778
Operation: Add

Time: 2018-09-15 11:09:59.782290
Object_id: 7779
Operation: Delete

""")

