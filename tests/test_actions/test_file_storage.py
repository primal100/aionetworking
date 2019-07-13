import asyncio
from pathlib import Path

from lib.actions.file_storage import ManagedFile


class TestASNFileStorage:

    def test_00_do_one(self, tmp_path, file_storage_action, asn_object, asn_encoded_multi, asn_codec):
        asyncio.run(file_storage_action.do_one(asn_object))
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        print(expected_file)
        assert expected_file.exists()
        print('exists')
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        msgs = asyncio.run(asn_codec.from_file(expected_file))
        assert msgs[0] == asn_object

    def test_01_do_many_close(self, tmp_path, file_storage_action, asn_objects, asn_encoded_multi):
        asyncio.run(file_storage_action.do_many_and_close(asn_objects))
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000002.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[1]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000003.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[2]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000004.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[3]

    def test_02_filter(self, file_storage_action, asn_object):
        assert file_storage_action.filter(asn_object) is False


class TestManagedFile:
    def test_00_get_file_close(self, tmp_path, managed_file):
        assert ManagedFile.num_files == 1
        ManagedFile.get_file(managed_file.path)
        assert ManagedFile.num_files == 1
        new_path = tmp_path/'managed_file2'
        f = ManagedFile.get_file(new_path)
        assert ManagedFile.num_files == 2
        asyncio.run(f.close())
        assert ManagedFile.num_files == 1

    def test_01_close_all(self, tmp_path):
        assert ManagedFile.num_files == 0
        ManagedFile.get_file(tmp_path/'managed_file1')
        ManagedFile.get_file(tmp_path / 'managed_file2')
        assert ManagedFile.num_files == 2
        asyncio.run(ManagedFile.close_all())
        assert ManagedFile.num_files == 0


class TestManagedFileASN:
    def test_00_write_and_wait(self, managed_file_path, asn_one_encoded):
        asyncio.run(ManagedFile.write_and_close(managed_file_path, asn_one_encoded))
        assert managed_file_path.read_bytes == asn_one_encoded


class TestASNBufferedFileStorage:

    def test_00_do_one(self, tmp_path, buffered_file_storage_action, asn_object, asn_encoded_multi, asn_codec):
        asyncio.run(buffered_file_storage_action.do_one(asn_object))
        expected_file = Path(tmp_path/'Encoded/10.10.10.10_TCAP_MAP.TCAPMAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        msgs = asyncio.run(asn_codec.from_file(expected_file))
        assert msgs[0] == asn_object

    def test_01_do_many_close(self, tmp_path, file_storage_action, asn_objects, asn_buffer, asn_codec):
        asyncio.run(file_storage_action.do_many_and_close(asn_objects))
        expected_file = Path(tmp_path/'Encoded/10.10.10.10_TCAP_MAP.TCAPMAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = asyncio.run(asn_codec.from_file(expected_file))
        assert msgs == asn_objects


class TestJsonFileStorage:

    def test_00_do_one(self, tmp_path, file_storage_action, json_object, json_encoded_multi, json_codec):
        asyncio.run(file_storage_action.do_one(json_object))
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/10.10.10.10_00000001.TCAPMAP')
        assert expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        msgs = asyncio.run(json_codec.from_file(expected_file))
        assert msgs[0] == json_object

    def test_01_do_many_close(self, tmp_path, file_storage_action, json_objects, json_encoded_multi):
        asyncio.run(file_storage_action.do_many_and_close(json_objects))
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/10.10.10.10_00000001.TCAPMAP')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/10.10.10.10_00000002.TCAPMAP')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[1]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/10.10.10.10_00000003.TCAPMAP')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[2]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/10.10.10.10_00000004.TCAPMAP')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[3]

    def test_02_filter(self, file_storage_action, json_object):
        assert file_storage_action.filter(json_object) is False


class TestManagedFileJson:
    def test_00_write_and_wait(self, managed_file_path, json_one_encoded):
        asyncio.run(ManagedFile.write_and_close(managed_file_path, json_one_encoded))
        assert managed_file_path.read_text() == json_one_encoded


class TestJsonBufferedFileStorage:

    def test_00_do_one(self, tmp_path, buffered_file_storage_action, json_object, json_encoded_multi, json_codec):
        asyncio.run(buffered_file_storage_action.do_one(json_object))
        expected_file = Path(tmp_path/'Encoded/10.10.10.10_TCAP_MAP.TCAPMAP')
        assert expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        msgs = asyncio.run(json_codec.from_file(expected_file))
        assert msgs[0] == json_object

    def test_01_do_many_close(self, tmp_path, file_storage_action, json_objects, json_buffer, json_codec):
        asyncio.run(file_storage_action.do_many_and_close(json_objects))
        expected_file = Path(tmp_path/'Encoded/10.10.10.10_TCAP_MAP.TCAPMAP')
        assert expected_file.exists()
        assert expected_file.read_text() == json_buffer
        msgs = asyncio.run(json_codec.from_file(expected_file))
        assert msgs == json_objects
