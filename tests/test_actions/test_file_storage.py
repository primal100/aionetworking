import pytest
import asyncio
import pickle
from pathlib import Path

from lib.actions.file_storage import ManagedFile
from lib.formats.recording import get_recording_from_file
from lib.utils import alist


class TestManagedFile:

    @pytest.mark.asyncio
    async def test_00_open_close(self, tmp_path, managed_file, append_mode):
        assert ManagedFile.num_files() == 1
        new_path = tmp_path/'managed_file2'
        f2 = ManagedFile.open(new_path, mode=append_mode)
        assert ManagedFile.num_files() == 2
        await f2.close()
        assert ManagedFile.num_files() == 1
        await managed_file.close()
        assert ManagedFile.num_files() == 0

    @pytest.mark.asyncio
    async def test_01_close_all(self, tmp_path, managed_file, append_mode):
        assert ManagedFile.num_files() == 1
        ManagedFile.open(tmp_path / 'managed_file2', mode=append_mode)
        assert ManagedFile.num_files() == 2
        await ManagedFile.close_all()
        assert ManagedFile.num_files() == 0


class TestJsonFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, file_storage_action, json_objects, json_rpc_login_request_encoded,
                             json_codec):
        await asyncio.wait([file_storage_action.do_one(obj) for obj in json_objects])
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_1.JSON')
        assert expected_file.exists()
        item = await json_codec.one_from_file(expected_file)
        assert item == json_objects[0]
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_2.JSON')
        assert expected_file.exists()
        item = await json_codec.one_from_file(expected_file)
        assert item == json_objects[1]

    def test_01_filter(self, file_storage_action, json_object):
        assert file_storage_action.filter(json_object) is False


class TestManagedFileJSON:
    @pytest.mark.asyncio
    async def test_00_writes(self, managed_file, json_objects, json_codec, json_buffer):
        await asyncio.wait([managed_file.write(obj.encoded) for obj in json_objects])
        items = await alist(json_codec.from_file(managed_file.path))
        assert sorted(items, key=str) == sorted(json_objects, key=str)


class TestJsonBufferedFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, buffered_file_storage_action, json_objects, json_buffer, json_codec):
        await asyncio.wait([buffered_file_storage_action.do_one(obj) for obj in json_objects])
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        items = await alist(json_codec.from_file(expected_file))
        assert sorted(items, key=str) == sorted(json_objects, key=str)

    @pytest.mark.asyncio
    async def test_01_pre_action(self, tmp_path, buffered_file_storage_recording_action, buffer_objects,
                                 json_recording_data, buffer_codec, timestamp):

        await buffered_file_storage_recording_action.do_one(buffer_objects[0])
        await buffered_file_storage_recording_action.do_one(buffer_objects[1])
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist(get_recording_from_file(expected_file))
        assert packets == json_recording_data

    def test_02_action_pickle(self, buffered_file_storage_action_binary):
        data = pickle.dumps(buffered_file_storage_action_binary)
        action = pickle.loads(data)
        assert action == buffered_file_storage_action_binary

    def test_03_pre_action_pickle(self, buffered_file_storage_pre_action_binary):
        data = pickle.dumps(buffered_file_storage_pre_action_binary)
        action = pickle.loads(data)
        assert action == buffered_file_storage_pre_action_binary
