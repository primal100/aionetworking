import pytest
from pathlib import Path

from lib.actions.file_storage import ManagedFile


class TestASNFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, file_storage_action_binary, asn_object, asn_encoded_multi, asn_codec):
        await file_storage_action_binary.do_one(asn_object)
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        assert expected_file.exists()
        print('exists')
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        obj = await asn_codec.one_from_file(expected_file)
        assert obj == asn_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, file_storage_action_binary, asn_objects, asn_encoded_multi):
        file_storage_action_binary.do_many(asn_objects)
        await file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_840001ff.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[1]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_a5050001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[2]
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000000.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[3]

    def test_02_filter(self, file_storage_action_binary, asn_object):
        assert file_storage_action_binary.filter(asn_object) is False


class TestManagedFile:

    @pytest.mark.asyncio
    async def test_00_get_file_close(self, tmp_path, managed_file_binary):
        assert ManagedFile.num_files() == 1
        new_path = tmp_path/'managed_file2'
        f2 = ManagedFile.get_file(new_path)
        assert ManagedFile.num_files() == 2
        await f2.close()
        assert ManagedFile.num_files() == 1
        await managed_file_binary.close()
        assert ManagedFile.num_files() == 0

    @pytest.mark.asyncio
    async def test_01_close_all(self, tmp_path, managed_file_binary):
        assert ManagedFile.num_files() == 1
        ManagedFile.get_file(tmp_path / 'managed_file2')
        assert ManagedFile.num_files() == 2
        await ManagedFile.close_all()
        assert ManagedFile.num_files() == 0


class TestManagedFileASN:
    @pytest.mark.asyncio
    async def test_00_write_and_wait(self, managed_file_binary, asn_objects, asn_codec, asn_buffer):
        for obj in asn_objects:
            managed_file_binary.write(obj)
        await managed_file_binary.close()
        assert managed_file_binary.path.read_bytes() == asn_buffer
        assert await asn_codec.from_file(managed_file_binary.path) == asn_objects


class TestASNBufferedFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, buffered_file_storage_action_binary, asn_object, asn_encoded_multi, asn_codec):
        buffered_file_storage_action_binary.do_one(asn_object)
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        msg = await asn_codec.one_from_file(expected_file)
        assert msg == asn_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, buffered_file_storage_action_binary, asn_objects, asn_buffer, asn_codec):
        buffered_file_storage_action_binary.do_many(asn_objects)
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = await asn_codec.from_file(expected_file)
        assert msgs == asn_objects


class TestJsonFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, file_storage_action_text, json_object, json_encoded_multi, json_codec):
        await file_storage_action_text.do_one(json_object)
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_0.JSON')
        assert expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        msg = await json_codec.one_from_file(expected_file)
        assert msg == json_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, file_storage_action_text, json_objects, json_encoded_multi):
        file_storage_action_text.do_many(json_objects)
        await file_storage_action_text.close()
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_0.JSON')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_1.JSON')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[1]

    def test_02_filter(self, file_storage_action_text, json_object):
        assert file_storage_action_text.filter(json_object) is False


class TestManagedFileJSON:
    @pytest.mark.asyncio
    async def test_00_write_and_wait(self, managed_file_text, json_objects, json_codec, json_buffer):
        for obj in json_objects:
            managed_file_text.write(obj)
        await managed_file_text.close()
        assert managed_file_text.path.read_text() == json_buffer
        assert await json_codec.from_file(managed_file_text.path) == json_objects


class TestJsonBufferedFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, buffered_file_storage_action_text, json_object, json_encoded_multi, json_codec):
        buffered_file_storage_action_text.do_one(json_object)
        await buffered_file_storage_action_text.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        obj = await json_codec.one_from_file(expected_file)
        assert obj == json_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, buffered_file_storage_action_text, json_objects, json_buffer, json_codec):
        buffered_file_storage_action_text.do_many(json_objects)
        await buffered_file_storage_action_text.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        assert expected_file.read_text() == json_buffer
        msgs = await json_codec.from_file(expected_file)
        assert msgs == json_objects
