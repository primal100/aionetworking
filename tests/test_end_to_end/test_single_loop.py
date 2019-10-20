import asyncio
import pytest
from pathlib import Path

from lib.actions.echo import InvalidRequestError

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, one_way_server_started, one_way_client, tmp_path, json_buffer,
                                              json_decoded_multi, json_recording_data):
        async with one_way_client as conn:
            conn.encode_and_send_msgs(json_decoded_multi)
            await asyncio.sleep(0.1) # Workaround for bpo-38471
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('Recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert expected_file.read_bytes() == json_buffer
        expected_file.unlink()
        new_recording_path = tmp_path / 'Recordings/new.recording'
        recording_file_path.rename(new_recording_path)
        async with one_way_client as conn:
            await conn.play_recording(new_recording_path)
            await asyncio.sleep(0.1)  # Workaround for bpo-38471
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(2), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert Path(expected_file).read_bytes() == json_buffer


class TestTwoWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, two_way_server_started, two_way_client, tmp_path, echo_response_object,
                                              echo_exception_response_object, echo_notification_object):
        async with two_way_client as conn:
            echo_response = await conn.echo()
            conn.subscribe()
            notification = await conn.wait_notification()
            await asyncio.sleep(0.1)  # Workaround for bpo-38471
        assert echo_response == echo_response_object
        assert notification == echo_notification_object
        recording_file_path = next(tmp_path.glob('Recordings/*.recording'))
        assert recording_file_path.exists()
        async with two_way_client as conn2:
            await conn2.play_recording(recording_file_path)
            echo_response = await asyncio.wait_for(conn2.wait_notification(), timeout=1)
            notification = await asyncio.wait_for(conn2.wait_notification(), timeout=1)
            await asyncio.sleep(0.1)  # Workaround for bpo-38471
        assert echo_response == echo_response_object
        assert notification == echo_notification_object
