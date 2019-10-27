import pytest
import asyncio
from pathlib import Path

from aionetworking.formats import get_recording_from_file
from aionetworking.utils import alist, time_coro


class TestOneWayReceiverAdaptor:
    def test_00_post_init(self, one_way_receiver_adaptor, json_codec, buffer_codec):
        assert one_way_receiver_adaptor.codec == json_codec
        assert one_way_receiver_adaptor.buffer_codec == buffer_codec

    @pytest.mark.asyncio
    async def test_01_on_data_received(self, tmp_path, one_way_receiver_adaptor, json_buffer,
                                       json_rpc_login_request_encoded, json_rpc_logout_request_encoded,
                                       timestamp, json_recording_data, json_codec, json_objects,
                                       buffered_file_storage_action):
        task1 = one_way_receiver_adaptor.on_data_received(json_rpc_login_request_encoded, timestamp)
        task2 = one_way_receiver_adaptor.on_data_received(json_rpc_logout_request_encoded, timestamp)
        await one_way_receiver_adaptor.close()
        assert task1.done()
        assert task2.done()
        expected_file = Path(tmp_path/'data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        assert expected_file.read_bytes() == json_buffer
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects
        expected_file = Path(tmp_path / 'recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist(get_recording_from_file(expected_file))
        assert packets == json_recording_data


class TestSenderAdaptorOneWay:
    def test_00_post_init(self, one_way_receiver_adaptor, json_codec):
        assert one_way_receiver_adaptor.codec == json_codec

    @pytest.mark.asyncio
    async def test_01_close(self, one_way_receiver_adaptor):
        await one_way_receiver_adaptor.close()

    @pytest.mark.asyncio
    async def test_02_send(self, one_way_sender_adaptor, json_rpc_login_request_encoded, queue):
        one_way_sender_adaptor.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == json_rpc_login_request_encoded

    @pytest.mark.asyncio
    async def test_03_send_data(self, one_way_sender_adaptor, json_rpc_login_request_encoded, queue):
        one_way_sender_adaptor.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == json_rpc_login_request_encoded

    def test_04_encode_and_send_msg(self, one_way_sender_adaptor, json_rpc_login_request_encoded,
                                    json_rpc_login_request, queue):
        one_way_sender_adaptor.encode_and_send_msg(json_rpc_login_request)
        assert queue.get_nowait() == json_rpc_login_request_encoded

    def test_05_encode_and_msgs(self, one_way_sender_adaptor, json_decoded_multi, json_encoded_multi, queue):
        one_way_sender_adaptor.encode_and_send_msgs(json_decoded_multi)
        assert [queue.get_nowait(), queue.get_nowait()] == json_encoded_multi

    @pytest.mark.asyncio
    async def test_06_play_recording(self, one_way_sender_adaptor, file_containing_json_recording: Path,
                                     json_encoded_multi, queue):
        await asyncio.wait_for(one_way_sender_adaptor.play_recording(file_containing_json_recording, timing=False),
                               timeout=0.1)
        assert [queue.get_nowait(), queue.get_nowait()] == json_encoded_multi

    @pytest.mark.asyncio
    async def test_07_play_recording_delay(self, one_way_sender_adaptor, file_containing_json_recording: Path,
                                           json_encoded_multi, queue):
        coro = one_way_sender_adaptor.play_recording(file_containing_json_recording, timing=True)
        time_taken = await time_coro(coro)
        assert [queue.get_nowait(), queue.get_nowait()] == json_encoded_multi
        assert time_taken > 1.1
