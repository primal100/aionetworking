import pytest
import asyncio
import pickle
from pathlib import Path

from lib.actions.file_storage import ManagedFile
from lib.utils import alist, Record


class TestASNFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, file_storage_action_binary, asn_object, asn_one_encoded, asn_codec):
        await file_storage_action_binary.async_do_one(asn_object)
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_one_encoded
        obj = await asn_codec.one_from_file(expected_file)
        assert obj == asn_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, file_storage_action_binary, asn_objects, asn_encoded_multi,
                                    task_scheduler):
        for asn_object in asn_objects:
            task_scheduler.schedule_task(file_storage_action_binary.async_do_one(asn_object),
                                              callback=task_scheduler.task_done)
        await asyncio.wait_for(task_scheduler.close(), timeout=1)
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

    def test_03_action_pickle(self, file_storage_action_binary):
        data = pickle.dumps(file_storage_action_binary)
        action = pickle.loads(data)
        assert action == file_storage_action_binary


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
    async def test_00_write_and_wait(self, managed_file_binary, asn_objects, asn_codec, asn_buffer, timestamp):
        for obj in asn_objects:
            managed_file_binary.write(obj)
        await managed_file_binary.close()
        assert managed_file_binary.path.read_bytes() == asn_buffer
        objects = asn_codec.from_file(managed_file_binary.path, received_timestamp=timestamp)
        assert await alist(objects) == asn_objects


class TestASNBufferedFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, buffered_file_storage_action_binary, asn_object, asn_one_encoded, asn_codec):
        buffered_file_storage_action_binary.do_many([asn_object])
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_one_encoded
        msg = await asn_codec.one_from_file(expected_file)
        assert msg == asn_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, buffered_file_storage_action_binary, asn_objects, asn_buffer, asn_codec):
        buffered_file_storage_action_binary.do_many(asn_objects)
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = await alist(asn_codec.from_file(expected_file))
        assert msgs == asn_objects

    @pytest.mark.asyncio
    async def test_02_pre_action(self, tmp_path, buffered_file_storage_pre_action_binary, buffer_object_asn1,
                                 buffer_object_asn2, asn1_recording, asn1_recording_data):
        buffered_file_storage_pre_action_binary.do_many([buffer_object_asn1])
        buffered_file_storage_pre_action_binary.do_many([buffer_object_asn2])
        await buffered_file_storage_pre_action_binary.close()
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == asn1_recording_data
        assert expected_file.read_bytes() == asn1_recording

    def test_03_action_pickle(self, buffered_file_storage_action_binary):
        data = pickle.dumps(buffered_file_storage_action_binary)
        action = pickle.loads(data)
        assert action == buffered_file_storage_action_binary

    def test_04_pre_action_pickle(self, buffered_file_storage_pre_action_binary):
        data = pickle.dumps(buffered_file_storage_pre_action_binary)
        action = pickle.loads(data)
        assert action == buffered_file_storage_pre_action_binary


class TestJsonFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, file_storage_action_text, json_object, json_rpc_login_request_encoded, json_codec):
        await file_storage_action_text.async_do_one(json_object)
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_1.JSON')
        assert expected_file.exists()
        assert expected_file.read_text() == json_rpc_login_request_encoded
        msg = await json_codec.one_from_file(expected_file)
        assert msg == json_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, file_storage_action_text, json_objects, json_encoded_multi,
                                    task_scheduler):
        for obj in json_objects:
            task_scheduler.schedule_task(file_storage_action_text.async_do_one(obj),
                                         callback=task_scheduler.task_done)
        await asyncio.wait_for(task_scheduler.close(), timeout=1)
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_1.JSON')
        expected_file.exists()
        assert expected_file.read_text() == json_encoded_multi[0]
        expected_file = Path(tmp_path/'Encoded/JSON/127.0.0.1_2.JSON')
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
        assert await alist(json_codec.from_file(managed_file_text.path)) == json_objects


class TestJsonBufferedFileStorage:

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, buffered_file_storage_action_text, json_object, json_rpc_login_request_encoded, json_codec):
        buffered_file_storage_action_text.do_many([json_object])
        await buffered_file_storage_action_text.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        assert expected_file.read_text() == json_rpc_login_request_encoded
        obj = await json_codec.one_from_file(expected_file)
        assert obj == json_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, buffered_file_storage_action_text, json_objects, json_buffer, json_codec):
        buffered_file_storage_action_text.do_many(json_objects)
        await buffered_file_storage_action_text.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        assert expected_file.read_text() == json_buffer
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects

    @pytest.mark.asyncio
    async def test_02_pre_action(self, tmp_path, buffered_file_storage_pre_action_text, buffer_object_json1,
                                 buffer_object_json2, json_recording, json_recording_data):
        buffered_file_storage_pre_action_text.do_many([buffer_object_json1])
        buffered_file_storage_pre_action_text.do_many([buffer_object_json2])
        await buffered_file_storage_pre_action_text.close()
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == json_recording_data
        assert expected_file.read_bytes() == json_recording
