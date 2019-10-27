import asyncio
from operator import attrgetter
import pytest
from pathlib import Path

from aionetworking.utils import alist
from aionetworking.actions.echo import InvalidRequestError

###Required for skipif in fixture params###
from aionetworking.compatibility import datagram_supported, supports_pipe_or_unix_connections


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, one_way_server_started, one_way_client, tmp_path, json_objects,
                                              json_decoded_multi, json_recording_data, one_way_server_context,
                                              one_way_client_context, connections_manager, json_codec):
        async with one_way_client as conn:
            conn.encode_and_send_msgs(json_decoded_multi)
            await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
            assert conn.context.keys() == one_way_client_context.keys()
            await asyncio.sleep(0.1) # Workaround for bpo-38471
        one_way_server_started.close_all_connections()
        await one_way_server_started.wait_num_connections(0)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        objs = await alist(json_codec.from_file(expected_file))
        objs.sort(key=attrgetter('request_id'), reverse=False)
        assert objs == json_objects
        expected_file.unlink()
        new_recording_path = tmp_path / 'recordings/new.recording'
        recording_file_path.rename(new_recording_path)
        async with one_way_client as conn:
            await conn.play_recording(new_recording_path)
            await asyncio.sleep(0.1)  # Workaround for bpo-38471
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(2), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        expected_file = next(Path(tmp_path / 'data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        objs = await alist(json_codec.from_file(expected_file))
        objs.sort(key=attrgetter('request_id'), reverse=False)
        assert objs == json_objects


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
        recording_file_path = next(tmp_path.glob('recordings/*.recording'))
        assert recording_file_path.exists()
        async with two_way_client as conn2:
            await conn2.play_recording(recording_file_path)
            echo_response = await asyncio.wait_for(conn2.wait_notification(), timeout=1)
            notification = await asyncio.wait_for(conn2.wait_notification(), timeout=1)
            await asyncio.sleep(0.1)  # Workaround for bpo-38471
        assert echo_response == echo_response_object
        assert notification == echo_notification_object
