import pytest

from lib.formats.contrib.TCAP_MAP import TCAPMAPASNObject
from lib.utils import alist


class TestASN1Codec:
    def test_00_set_context(self, asn_codec_empty_context, context):
        asn_codec_empty_context.set_context(context)
        assert asn_codec_empty_context.context == context

    def test_01_decode(self, asn_codec, asn_buffer, asn_encoded_multi, asn_decoded_multi):
        decoded = list(asn_codec.decode(asn_buffer))
        assert decoded == [(e, asn_decoded_multi[i]) for i, e in enumerate(asn_encoded_multi)]

    def test_02_encode(self, asn_codec, asn_one_decoded, asn_one_encoded):
        encoded = asn_codec.encode(asn_one_decoded)
        assert encoded == asn_one_encoded

    def test_03_decode_buffer(self, asn_codec, asn_buffer, asn_objects, timestamp):
        decoded = list(asn_codec.decode_buffer(asn_buffer, received_timestamp=timestamp))
        assert decoded == asn_objects

    def test_04_from_decoded(self, asn_codec, asn_one_decoded, asn_object, asn_objects, timestamp, asn_decoded_multi,
                             asn_encoded_multi):
        for i, decoded in enumerate(asn_decoded_multi):
            msg_obj = asn_codec.from_decoded(decoded, received_timestamp=timestamp)
            assert msg_obj.decoded == decoded
            assert msg_obj.encoded == asn_encoded_multi[i]
            assert msg_obj == asn_objects[i]

    @pytest.mark.asyncio
    async def test_05_from_file_many(self, asn_codec, file_containing_multi_asn, asn_objects, timestamp):
        objects = asn_codec.from_file(file_containing_multi_asn, received_timestamp=timestamp)
        assert await alist(objects) == asn_objects

    @pytest.mark.asyncio
    async def test_06_from_file_one(self, asn_codec, file_containing_asn, asn_object, timestamp):
        obj = await asn_codec.one_from_file(file_containing_asn, received_timestamp=timestamp)
        assert obj == asn_object


class TestASN1Object:
    def test_00_get_codec(self, asn_codec, context):
        codec = TCAPMAPASNObject.get_codec(context=context)
        assert codec == asn_codec

    def test_00_properties(self, asn_object, timestamp):
        assert asn_object.sender == '127.0.0.1'
        assert asn_object.full_sender == '127.0.0.1:8888'
        assert asn_object.otid == b'00000001'
        assert asn_object.uid == '00000001'
        assert asn_object.request_id is None
        assert asn_object.event_type == 'begin'
        assert asn_object.domain == '0.0.17.773.1.1.1'
        assert asn_object.timestamp == timestamp
        assert str(asn_object) == 'TCAP_MAP 00000001'

    def test_01_filter(self, asn_object):
        assert asn_object.filter() is False

    def test_02_subscribe_unsubscribe(self, asn_object, connections_manager, simple_network_connection):
        connections_manager.add_connection(simple_network_connection)
        asn_object.subscribe("test")
        assert asn_object.is_subscribed("test") is True
        asn_object.unsubscribe("test")
        assert asn_object.is_subscribed("test") is False

    def test_03_processed(self, asn_object):
        pass

