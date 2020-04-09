import pytest
import asyncio
from pathlib import Path

from aionetworking.utils import time_coro


@pytest.mark.connections('all_oneway_server')
class TestOneWayReceiverAdaptor:
    @pytest.mark.asyncio
    async def test_00_on_data_received(self, adaptor, json_rpc_login_request_encoded, json_rpc_logout_request_encoded,
                                       timestamp, json_codec, buffer_codec, assert_recordings_ok,
                                       assert_buffered_file_storage_ok):
        task1 = adaptor.on_data_received(json_rpc_login_request_encoded, timestamp)
        task2 = adaptor.on_data_received(json_rpc_logout_request_encoded, timestamp)
        assert adaptor.codec == json_codec
        assert adaptor.buffer_codec == buffer_codec
        await adaptor.close()
        await asyncio.wait_for(task1, 0.1)
        await asyncio.wait_for(task2, 0.1)
        await assert_buffered_file_storage_ok
        await assert_recordings_ok


@pytest.mark.connections('all_oneway_client')
class TestSenderAdaptorOneWay:

    @pytest.mark.asyncio
    async def test_00_send(self, adaptor, json_rpc_login_request_encoded, queue):
        adaptor.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == json_rpc_login_request_encoded

    @pytest.mark.asyncio
    async def test_01_send_data(self, adaptor, json_rpc_login_request_encoded, queue):
        adaptor.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == json_rpc_login_request_encoded

    @pytest.mark.asyncio
    async def test_02_encode_and_send_msg(self, adaptor, json_rpc_login_request_encoded, json_rpc_login_request, queue,
                                          json_codec):
        adaptor.encode_and_send_msg(json_rpc_login_request)
        assert adaptor.codec == json_codec
        assert await asyncio.wait_for(queue.get(), 1) == json_rpc_login_request_encoded

    @pytest.mark.asyncio
    async def test_03_encode_and_send_msgs(self, adaptor, json_decoded_multi, json_encoded_multi, queue):
        adaptor.encode_and_send_msgs(json_decoded_multi)
        assert [await asyncio.wait_for(queue.get(), 1), await asyncio.wait_for(queue.get(), 1)] == json_encoded_multi

    @pytest.mark.asyncio
    async def test_04_play_recording(self, adaptor, file_containing_json_recording: Path,
                                     json_encoded_multi, queue):
        await asyncio.wait_for(adaptor.play_recording(file_containing_json_recording, timing=False),
                               timeout=0.1)
        assert [await asyncio.wait_for(queue.get(), 1), await asyncio.wait_for(queue.get(), 1)] == json_encoded_multi

    @pytest.mark.asyncio
    async def test_05_play_recording_delay(self, adaptor, file_containing_json_recording: Path,
                                           json_encoded_multi, queue):
        coro = adaptor.play_recording(file_containing_json_recording, timing=True)
        time_taken = await time_coro(coro)
        assert [await asyncio.wait_for(queue.get(), 1), await asyncio.wait_for(queue.get(), 1)] == json_encoded_multi
        assert time_taken > 1.1
