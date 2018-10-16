from lib.basetestcase import BaseTestCase
from lib.protocols.contrib.json_sample import JsonSampleProtocol


class JsonSampleInterfaceTestcase(BaseTestCase):
    protocol = JsonSampleProtocol
    sender = "192.168.1.2"
    encoded_json = '{"id": 0, "actions": [{"timestamp": 1537006771.033925, "operation": "modify", "object_id": 1234}, {"timestamp": 1537006782.641033, "operation": "add", "object_id": 2222}, {"timestamp": 1537006798.78229, "operation": "delete", "object_id": 173}]}'

    def setUp(self):
        self.interface = self.protocol(self.sender, self.encoded_json)

    def test_00_decoded(self):
        self.assertDictEqual(self.interface.decoded, {'id': 0, 'actions': [
            {'timestamp': 1537006771.033925, 'operation': 'modify', 'object_id': 1234},
            {'timestamp': 1537006782.641033, 'operation': 'add', 'object_id': 2222},
            {'timestamp': 1537006798.78229, 'operation': 'delete', 'object_id': 173}]}
                             )

    def test_01_uid(self):
        result = self.interface.uid
        self.assertEqual(result, 0)

    def test_02_prettified(self):
        self.assertListEqual(self.interface.prettified,
  [{'time': '2018-09-15 11:09:31.033925', 'object_id': 1234, 'operation': 'Modify'},
                        {'time': '2018-09-15 11:09:42.641033', 'object_id': 2222, 'operation': 'Add'},
                        {'time': '2018-09-15 11:09:58.782290', 'object_id': 173, 'operation': 'Delete'}]
        )

    def test_03_interface_name(self):
        result = self.interface.get_protocol_name()
        self.assertEqual(result, 'JsonLogHandler')

    def test_04_storage_path(self):
        result = self.interface.storage_path
        self.assertPathEqual(result, 'JsonLogHandler')

    def test_05_file_extension(self):
        result = self.interface.file_extension
        self.assertEqual(result, 'json')

    def test_07_storage_path_single(self):
        result = self.interface.storage_path_single
        self.assertPathEqual(result, 'JsonLogHandler')

    def test_08_storage_path_multiple(self):
        result = self.interface.storage_path_multiple
        self.assertPathEqual(result, 'JsonLogHandler')

    def test_09_storage_filename_single(self):
        result = self.interface.storage_filename_single
        self.assertEqual(result, '192.168.1.2_0')

    def test_10_storage_filename_multiple(self):
        result = self.interface.storage_filename_multiple
        self.assertEqual(result, '192.168.1.2_JsonLogHandler')

    def test_11_summaries(self):
        result = self.interface.summaries
        self.assertListEqual(result, [
            ('2018-09-15 11:09:31.033925', 1234, 'Modify'),
            ('2018-09-15 11:09:42.641033', 2222, 'Add'),
            ('2018-09-15 11:09:58.782290', 173, 'Delete')
        ])
