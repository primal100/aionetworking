import asyncio

from lib.formats.contrib.json import JSONObject


class TestJsonCodec:
    def test_00_set_context(self, json_codec):
        json_codec.set_context({'sender': 'localhost'})
        assert json_codec.context == {'sender': 'localhost'}

    def test_01_decode(self, json_codec, json_buffer, json_encoded_multi, json_decoded_multi):
        decoded = list(json_codec.decode(json_buffer))
        assert decoded == [(e, json_decoded_multi[i]) for i, e in enumerate(json_encoded_multi)]

    def test_02_encode(self, json_codec, json_rpc_request, json_one_encoded):
        encoded = json_codec.encode(json_rpc_request)
        assert encoded == json_one_encoded

    def test_03_from_buffer(self, json_codec, json_buffer, json_objects, timestamp):
        decoded = json_codec.from_buffer(json_buffer, received_timestamp=timestamp)
        assert decoded == json_objects

    def test_04_from_decoded(self, json_codec, json_rpc_request, json_object, timestamp):
        encoded = json_codec.from_decoded(json_rpc_request, received_timestamp=timestamp)
        assert encoded == json_object

    def test_05_create_msg(self, json_codec, json_rpc_request, json_object, timestamp):
        obj = json_codec.create_msg(json_rpc_request, received_timestamp=timestamp)
        assert obj == json_object

    def test_06_from_file(self, json_codec, file_containing_json, json_object, timestamp):
        obj = asyncio.run(json_codec.from_file(file_containing_json, received_timestamp=timestamp))[0]
        assert obj == json_object


class TestJsonObject:
    def test_00_get_codec(self, json_codec):
        codec = JSONObject.get_codec(context={'sender': '127.0.0.1'})
        assert codec == json_codec

    def test_00_properties(self, json_object, timestamp):
        assert json_object.sender == '127.0.0.1'
        assert json_object.uid == 0
        assert json_object.request_id == 0
        assert json_object.timestamp == timestamp
        assert str(json_object) == 'JSON 0'

    def test_01_filter(self, json_object):
        assert json_object.filter() is False

    def test_02_processed(self, json_object):
        pass

