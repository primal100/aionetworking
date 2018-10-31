from lib.basetestcase import BaseTestCase
from pathlib import Path
import shutil

from lib.actions import text
from lib.protocols.contrib.json_sample import JsonSampleProtocol


class TestTextActionJSON(BaseTestCase):
    protocol = JsonSampleProtocol
    encoded_json = '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}'
    encoded_jsons = [
        '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}',
        '{"id": 1, "actions": [{"timestamp": 1537006775.033925, "operation": "modify", "object_id": 7777}, {"timestamp": 1537006792.641033, "operation": "add", "object_id": 7778}, {"timestamp": 1537006799.78229, "operation": "delete", "object_id": 7779}]}'
    ]
    sender = '10.10.10.10'
    maxDiff = None

    def setUp(self):
        try:
            shutil.rmtree(Path(self.base_data_dir, 'Encoded'))
        except OSError:
            pass
        self.action = text.Action(self.base_data_dir.joinpath(text.Action.default_data_dir))
        self.print_action = text.Action(storage=False)
        self.msg = self.protocol(self.sender, self.encoded_json)
        self.msgs = [self.protocol(self.sender, encoded_json) for encoded_json in self.encoded_jsons]

    def test_00_content(self):
        content = self.action.get_content(self.msg)
        self.assertEqual(content,
                         '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}'
                         )

    def test_01_print_msg(self):
        result = self.print_action.print_msg(self.msg)
        self.assertEqual(result,
                         """('{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": '
 '"modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": '
 '"add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": '
 '"delete", "object_id": 173}]}')""")

    def test_02_print(self):
        self.print_action.print(self.msg)

    def test_03_get_extension(self):
        result = self.action.get_file_extension(self.msg)
        self.assertEqual(result, 'json')

    def test_04_get_extension_multi(self):
        result = self.action.get_multi_file_extension(self.msg)
        self.assertEqual(result, 'json')

    def test_05_writes_for_store_many(self):
        result = self.action.writes_for_store_many(self.msgs)
        self.assertDictEqual(result,
                             {
                                 Path('10.10.10.10_JsonLogHandler.json'): '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}\n{"id": 1, "actions": [{"timestamp": 1537006775.033925, "operation": "modify", "object_id": 7777}, {"timestamp": 1537006792.641033, "operation": "add", "object_id": 7778}, {"timestamp": 1537006799.78229, "operation": "delete", "object_id": 7779}]}\n'}
                                      )

    def test_06_do(self):
        self.action.do(self.msg)
        expected_file = Path(self.base_data_dir, 'Encoded', 'JsonLogHandler', '10.10.10.10_0.json')
        self.assertFileContentsEqual(expected_file,
                                     '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}'
                                     )
        msg = self.protocol.from_file(self.sender, expected_file)
        self.assertDictEqual(msg.decoded,
                             {'id': 0,
                              'actions': [{'timestamp': 1537006771.033925, 'operation': 'modify', 'object_id': 1234},
                                          {'timestamp': 1537006782.641033, 'operation': 'add', 'object_id': 2222},
                                          {'timestamp': 1537006798.78229, 'operation': 'delete', 'object_id': 173}]}
                             )

    def test_07_do_many(self):
        self.action.do_multiple(self.msgs)
        expected_file = Path(self.base_data_dir, 'Encoded', '10.10.10.10_JsonLogHandler.json')
        self.assertFileContentsEqual(expected_file,
"""{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}
{"id": 1, "actions": [{"timestamp": 1537006775.033925, "operation": "modify", "object_id": 7777}, {"timestamp": 1537006792.641033, "operation": "add", "object_id": 7778}, {"timestamp": 1537006799.78229, "operation": "delete", "object_id": 7779}]}
"""
                                     )
        msgs = self.protocol.from_file_multi(self.sender, expected_file)
        self.assertSequenceEqual(self.encoded_jsons, [msg.encoded for msg in msgs])
        self.assertSequenceEqual([msg.decoded for msg in self.msgs], [msg.decoded for msg in msgs])
