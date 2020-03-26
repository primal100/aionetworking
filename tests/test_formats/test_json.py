import pytest
import asyncio
from aionetworking.formats.contrib.json import JSONObject
from aionetworking.formats.recording import get_recording
from aionetworking.utils import alist


class TestJsonCodec:

    @pytest.mark.asyncio
    async def test_00_decode(self, json_codec, json_buffer, decoded_result):
        decoded = await alist(json_codec.decode(json_buffer))
        assert decoded == decoded_result

    @pytest.mark.asyncio
    async def test_01_encode(self, json_codec, json_rpc_login_request, json_rpc_login_request_encoded):
        encoded = await json_codec.encode(json_rpc_login_request)
        assert encoded == json_rpc_login_request_encoded

    @pytest.mark.asyncio
    async def test_02_decode_buffer(self, json_codec, json_buffer, json_objects, timestamp):
        decoded = await alist(json_codec.decode_buffer(json_buffer, system_timestamp=timestamp))
        assert decoded == json_objects

    @pytest.mark.asyncio
    async def test_03_encode_obj(self, json_codec, json_rpc_login_request, json_object, timestamp):
        encoded = await json_codec.encode_obj(json_rpc_login_request, system_timestamp=timestamp)
        assert encoded == json_object

    @pytest.mark.asyncio
    async def test_04_from_file_many(self, json_codec, file_containing_multi_json, json_objects, timestamp):
        objects = json_codec.from_file(file_containing_multi_json, system_timestamp=timestamp)
        assert await alist(objects) == json_objects

    @pytest.mark.asyncio
    async def test_05_from_file(self, json_codec, file_containing_multi_json, json_object, timestamp):
        obj = await json_codec.one_from_file(file_containing_multi_json, system_timestamp=timestamp)
        assert obj == json_object
        await asyncio.get_event_loop().shutdown_asyncgens()


class TestJsonObject:
    def test_00_get_codec(self, json_buffer, json_codec, context):
        codec = JSONObject.get_codec(json_buffer, context=context)
        assert codec == json_codec

    def test_01_properties(self, json_object, timestamp, client_sock, client_sock_str, client_hostname):
        assert json_object.peer == client_sock_str
        assert json_object.address == client_sock[0]
        assert json_object.sender == client_hostname
        assert json_object.uid == 1
        assert json_object.request_id == 1
        assert json_object.timestamp == timestamp
        assert str(json_object) == 'JSON 1'

    def test_02_filter(self, json_object):
        assert json_object.filter() is False

    def test_03_json_object_with_codec_kwargs(self, json_buffer, json_object_with_codec_kwargs, json_codec_with_kwargs):
        codec = json_object_with_codec_kwargs.get_codec(json_buffer, test_param='abc')
        assert codec == json_codec_with_kwargs


class TestBufferObject:
    @pytest.mark.asyncio
    async def test_00_buffer_recording(self, buffer_codec, json_encoded_multi, json_recording_data, context, timestamp):
        buffer_obj1 = await buffer_codec.encode_obj(json_encoded_multi[0], system_timestamp=timestamp)
        buffer_obj2 = await buffer_codec.encode_obj(json_encoded_multi[1], system_timestamp=timestamp)
        recording = buffer_obj1.encoded + buffer_obj2.encoded
        packets = await alist(get_recording(recording))
        assert packets == json_recording_data
