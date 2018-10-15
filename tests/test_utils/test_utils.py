from unittest import TestCase
from lib import utils


class UtilsTestCase(TestCase):

    def test_pack_unpack_binary(self):
        bytes_list = [
            b'L\xcf\xd3\x98',
            b'\x9b\xb5\x96\x9a\xcd\xf6\x8d>#\xd4',
            b'\x16\t\xcd*7\x9a',
            b'\xf0s\xc6'
        ]

        packed = utils.pack_variable_len_string(bytes_list[0])
        self.assertEqual(packed, b'\x04\x00\x00\x00L\xcf\xd3\x98')
        packed += utils.pack_variable_len_string(bytes_list[1])
        self.assertEqual(packed, b'\x04\x00\x00\x00L\xcf\xd3\x98\n\x00\x00\x00\x9b\xb5\x96\x9a\xcd\xf6\x8d>#\xd4')
        packed += utils.pack_variable_len_string(bytes_list[2])
        self.assertEqual(packed,
                         b'\x04\x00\x00\x00L\xcf\xd3\x98\n\x00\x00\x00\x9b\xb5\x96\x9a\xcd\xf6\x8d>#\xd4\x06\x00\x00\x00\x16\t\xcd*7\x9a')
        packed += utils.pack_variable_len_string(bytes_list[3])
        self.assertEqual(packed, b'\x04\x00\x00\x00L\xcf\xd3\x98\n\x00\x00\x00\x9b\xb5\x96\x9a\xcd\xf6\x8d>#\xd4\x06\x00\x00\x00\x16\t\xcd*7\x9a\x03\x00\x00\x00\xf0s\xc6')
        restored_bytes_list = utils.unpack_variable_len_strings(packed)
        self.assertListEqual(restored_bytes_list, bytes_list)
