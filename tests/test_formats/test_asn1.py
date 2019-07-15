import pytest

from lib.formats.contrib.TCAP_MAP import TCAPMAPASNObject


class TestASN1Codec:
    def test_00_set_context(self, asn_codec):
        asn_codec.set_context({'sender': 'localhost'})
        assert asn_codec.context == {'sender': 'localhost'}

    def test_01_decode(self, asn_codec, asn_buffer, asn_encoded_multi, asn_decoded_multi):
        decoded = list(asn_codec.decode(asn_buffer))
        assert decoded == [(e, asn_decoded_multi[i]) for i, e in enumerate(asn_encoded_multi)]

    def test_02_encode(self, asn_codec, asn_one_decoded, asn_one_encoded):
        encoded = asn_codec.encode(asn_one_decoded)
        assert encoded == asn_one_encoded

    def test_03_from_buffer(self, asn_codec, asn_buffer, asn_objects, timestamp):
        decoded = asn_codec.from_buffer(asn_buffer, received_timestamp=timestamp)
        assert decoded == asn_objects

    def test_04_from_decoded(self, asn_codec, asn_one_decoded, asn_object, timestamp):
        encoded = asn_codec.from_decoded(asn_one_decoded, received_timestamp=timestamp)
        assert encoded == asn_object

    def test_05_create_msg(self, asn_codec, asn_one_decoded, asn_object, timestamp):
        obj = asn_codec.create_msg(asn_one_decoded, received_timestamp=timestamp)
        assert obj == asn_object

    @pytest.mark.asyncio
    async def test_06_from_file(self, asn_codec, file_containing_asn, asn_object, timestamp):
        obj = await asn_codec.one_from_file(file_containing_asn, received_timestamp=timestamp)
        assert obj == asn_object


class TestASN1Object:
    def test_00_get_codec(self, asn_codec):
        codec = TCAPMAPASNObject.get_codec(context={'sender': '127.0.0.1'})
        assert codec == asn_codec

    def test_00_properties(self, asn_object, timestamp):
        assert asn_object.sender == '127.0.0.1'
        assert asn_object.otid == b'00000001'
        assert asn_object.uid == '00000001'
        assert asn_object.request_id is None
        assert asn_object.event_type == 'begin'
        assert asn_object.domain == '0.0.17.773.1.1.1'
        assert asn_object.timestamp == timestamp
        assert str(asn_object) == 'TCAP_MAP 00000001'

    def test_01_filter(self, asn_object):
        assert asn_object.filter() is False

    def test_02_processed(self, asn_object):
        pass

