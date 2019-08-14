import pytest
import asyncio
from datetime import timedelta
from pathlib import Path

from lib.utils import Record, alist, time_coro


class TestOneWayReceiverAdaptor:
    def test_00_post_init(self, one_way_receiver_adaptor, asn_codec):
        assert one_way_receiver_adaptor.codec == asn_codec

    @pytest.mark.asyncio
    async def test_01_close(self, one_way_receiver_adaptor):
        await one_way_receiver_adaptor.close()

    @pytest.mark.asyncio
    async def test_02_manage_buffer(self, tmp_path, one_way_receiver_adaptor, buffer_asn1_1, buffer_asn1_2, timestamp,
                                    asn1_recording, asn1_recording_data, buffered_file_storage_pre_action_binary):
        one_way_receiver_adaptor._manage_buffer(buffer_asn1_1, timestamp)
        one_way_receiver_adaptor._manage_buffer(buffer_asn1_2, timestamp + timedelta(seconds=1))
        await one_way_receiver_adaptor.close()
        await buffered_file_storage_pre_action_binary.close()
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == asn1_recording_data
        assert expected_file.read_bytes() == asn1_recording

    @pytest.mark.asyncio
    async def test_03_process_msgs(self, tmp_path, one_way_receiver_adaptor, asn_buffer, timestamp, asn_codec,
                                   asn_objects, buffered_file_storage_action_binary):
        one_way_receiver_adaptor.process_msgs(asn_objects, asn_buffer)
        await one_way_receiver_adaptor.close()
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        msgs = await alist(asn_codec.from_file(expected_file))
        assert msgs == asn_objects
        assert expected_file.read_bytes() == asn_buffer

    @pytest.mark.asyncio
    async def test_04_on_data_received(self, tmp_path, one_way_receiver_adaptor, asn_buffer, buffer_asn1_1,
                                       buffer_asn1_2, timestamp, asn1_recording, asn1_recording_data, asn_codec,
                                       asn_objects, buffered_file_storage_action_binary):
        one_way_receiver_adaptor.on_data_received(buffer_asn1_1, timestamp)
        one_way_receiver_adaptor.on_data_received(buffer_asn1_2, timestamp + timedelta(seconds=1))
        await one_way_receiver_adaptor.close()
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = await alist(asn_codec.from_file(expected_file))
        assert msgs == asn_objects
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn1_recording
        packets = list(Record.from_file(expected_file))
        assert packets == asn1_recording_data


class TestSenderAdaptorOneWay:
    def test_00_post_init(self, one_way_receiver_adaptor, asn_codec):
        assert one_way_receiver_adaptor.codec == asn_codec

    @pytest.mark.asyncio
    async def test_01_close(self, one_way_receiver_adaptor):
        await one_way_receiver_adaptor.close()

    def test_02_send(self, one_way_sender_adaptor, asn_one_encoded, deque):
        one_way_sender_adaptor.send(asn_one_encoded)
        assert deque.pop() == asn_one_encoded

    def test_03_send_data(self, one_way_sender_adaptor, asn_one_encoded, deque):
        one_way_sender_adaptor.send_data(asn_one_encoded)
        assert deque.pop() == asn_one_encoded

    def test_04_send_hex(self, one_way_sender_adaptor, asn_encoded_hex, asn_one_encoded, deque):
        one_way_sender_adaptor.send_hex(asn_encoded_hex[0])
        assert deque.pop() == asn_one_encoded

    def test_05_send_hex_msgs(self, one_way_sender_adaptor, asn_encoded_hex, asn_encoded_multi, deque):
        one_way_sender_adaptor.send_hex_msgs(asn_encoded_hex)
        assert list(deque) == asn_encoded_multi

    def test_07_encode_and_send_msg(self, one_way_sender_adaptor, asn_one_decoded, asn_one_encoded, deque):
        one_way_sender_adaptor.encode_and_send_msg(asn_one_decoded)
        assert deque.pop() == asn_one_encoded

    def test_08_encode_and_msgs(self, one_way_sender_adaptor, asn_decoded_multi, asn_encoded_multi, deque):
        one_way_sender_adaptor.encode_and_send_msgs(asn_decoded_multi)
        assert list(deque) == asn_encoded_multi

    @pytest.mark.asyncio
    async def test_09_play_recording(self, one_way_sender_adaptor, file_containing_asn1_recording, buffer_asn1_1, buffer_asn1_2, deque):
        await asyncio.wait_for(one_way_sender_adaptor.play_recording(file_containing_asn1_recording, timing=False),
                               timeout=0.1)
        assert list(deque) == [buffer_asn1_1, buffer_asn1_2]

    @pytest.mark.asyncio
    async def test_10_play_recording_delay(self, one_way_sender_adaptor, file_containing_asn1_recording, buffer_asn1_1,
                                           buffer_asn1_2, deque):
        coro = one_way_sender_adaptor.play_recording(file_containing_asn1_recording, timing=True)
        time_taken = await time_coro(coro)
        assert list(deque) == [buffer_asn1_1, buffer_asn1_2]
        assert time_taken > 1.0
