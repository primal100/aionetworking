import pytest

from lib.formats.contrib.json import JSONObject
from lib.utils import alist


class TestJsonCodec:

    def test_00_decode(self, json_codec, json_buffer, json_encoded_multi, json_decoded_multi):
        decoded = list(json_codec.decode(json_buffer))
        result = [(e, json_decoded_multi[i]) for i, e in enumerate(json_encoded_multi)]
        assert decoded == result

    def test_01_encode(self, json_codec, json_rpc_login_request, json_rpc_login_request_encoded):
        encoded = json_codec.encode(json_rpc_login_request)
        assert encoded == json_rpc_login_request_encoded

    def test_02_decode_buffer(self, json_codec, json_buffer, json_objects, timestamp):
        decoded = list(json_codec.decode_buffer(json_buffer, received_timestamp=timestamp))
        assert decoded == json_objects

    def test_03_from_decoded(self, json_codec, json_rpc_login_request, json_object, timestamp):
        encoded = json_codec.from_decoded(json_rpc_login_request, received_timestamp=timestamp)
        assert encoded == json_object

    @pytest.mark.asyncio
    async def test_04_from_file_many(self, json_codec, file_containing_multi_json, json_objects, timestamp):
        objects = json_codec.from_file(file_containing_multi_json, received_timestamp=timestamp)
        assert await alist(objects) == json_objects

    @pytest.mark.asyncio
    async def test_05_from_file(self, json_codec, file_containing_json, json_object, timestamp):
        obj = await json_codec.one_from_file(file_containing_json, received_timestamp=timestamp)
        assert obj == json_object


class TestJsonObject:
    def test_00_get_codec(self, json_codec, context):
        codec = JSONObject.get_codec(context=context)
        assert codec == json_codec

    def test_01_properties(self, json_object, timestamp):
        assert json_object.sender == '127.0.0.1'
        assert json_object.full_sender == '127.0.0.1:60000'
        assert json_object.uid == 1
        assert json_object.request_id == 1
        assert json_object.timestamp == timestamp
        assert str(json_object) == 'JSON 1'

    def test_02_filter(self, json_object):
        assert json_object.filter() is False

    def test_03_subscribe_unsubscribe(self, json_object, connections_manager, simple_network_connection):
        connections_manager.add_connection(simple_network_connection)
        json_object.subscribe("test")
        assert json_object.is_subscribed("test") is True
        json_object.unsubscribe("test")
        assert json_object.is_subscribed("test") is False

    def test_04_processed(self, json_object):
        pass

