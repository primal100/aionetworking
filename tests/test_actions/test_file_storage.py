import pytest
import asyncio
import pickle

from aionetworking.actions.file_storage import ManagedFile
from aionetworking.formats import get_recording_from_file
from aionetworking.utils import alist


class TestManagedFile:

    @pytest.mark.asyncio
    async def test_00_open_close(self, data_dir, managed_file):
        assert ManagedFile.num_files() == 1
        new_path = data_dir/'managed_file2'
        f2 = ManagedFile.open(new_path, mode='ab')
        assert ManagedFile.num_files() == 2
        await f2.close()
        assert ManagedFile.num_files() == 1
        await managed_file.close()
        assert ManagedFile.num_files() == 0

    @pytest.mark.asyncio
    async def test_01_close_all(self, data_dir, managed_file):
        assert ManagedFile.num_files() == 1
        ManagedFile.open(data_dir / 'managed_file2', mode='ab')
        assert ManagedFile.num_files() == 2
        await ManagedFile.close_all()
        assert ManagedFile.num_files() == 0

    @pytest.mark.asyncio
    async def test_02_writes(self, managed_file, json_objects, json_codec, json_buffer):
        await asyncio.wait([managed_file.write(obj.encoded) for obj in json_objects])
        items = await alist(json_codec.from_file(managed_file.path))
        assert sorted(items, key=str) == sorted(json_objects, key=str)


class TestFileStorageShared:

    @pytest.mark.asyncio
    async def test_00_do_one(self, data_dir, file_storage, json_objects, json_rpc_login_request_encoded,
                             json_codec, expected_action_files):
        await asyncio.wait([file_storage.do_one(obj) for obj in json_objects])
        for path, objects in expected_action_files.items():
            assert path.exists()
            items = await alist(json_codec.from_file(path))
            assert sorted(items, key=str) == sorted(objects, key=str)

    def test_01_filter(self, file_storage, json_object):
        assert file_storage.filter(json_object) is False

    @pytest.mark.asyncio
    async def test_02_do_one_response(self, data_dir, file_storage, keepalive_object):
        response = await file_storage.do_one(keepalive_object)
        assert not data_dir.exists()
        assert response == {'result': 'keepalive-response'}

    def test_03_action_pickle(self, file_storage):
        data = pickle.dumps(file_storage)
        action = pickle.loads(data)
        assert action == file_storage

    def test_04_pre_action_pickle(self, file_storage):
        data = pickle.dumps(file_storage)
        action = pickle.loads(data)
        assert action == file_storage


class TestJsonBufferedFileStorage:

    @pytest.mark.asyncio
    async def test_00_pre_action(self, recordings_dir, buffered_file_storage_recording_action, buffer_objects,
                                 json_recording_data, buffer_codec):

        await buffered_file_storage_recording_action.do_one(buffer_objects[0])
        await buffered_file_storage_recording_action.do_one(buffer_objects[1])
        expected_file = recordings_dir / '127.0.0.1.recording'
        assert expected_file.exists()
        packets = await alist(get_recording_from_file(expected_file))
        assert packets == json_recording_data

