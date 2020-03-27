import asyncio
from operator import attrgetter
import pytest
from pathlib import Path

from aionetworking.utils import alist
from aionetworking.actions.echo import InvalidRequestError

###Required for skipif in fixture params###
from aionetworking.compatibility import datagram_supported, supports_pipe_or_unix_connections, \
    supports_pipe_or_unix_connections_in_other_process


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, one_way_server_started, one_way_client, tmp_path, json_objects,
                                              json_decoded_multi, json_recording_data, one_way_server_context,
                                              one_way_client_context, connections_manager, json_codec):
        async with one_way_client as conn:
            conn.encode_and_send_msgs(json_decoded_multi)
            await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), 3)
            assert conn.context.keys() == one_way_client_context.keys()
            await asyncio.sleep(0.1) # Workaround for bpo-38471
        one_way_server_started.close_all_connections()
        await one_way_server_started.wait_num_connections(0)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), 3)
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
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(2), 3)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), 3)
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

    @pytest.mark.asyncio
    async def test_01_send_multiple_senders(self, reset_endpoint_names, tcp_server_two_way_started, tcp_client_two_way,
                                            tcp_client_two_way_two, tmp_path, echo_response_object,
                                            echo_exception_response_object, echo_notification_object, server_sock_str):
        assert tcp_server_two_way_started.protocol_factory.full_name == f"TCP Server {server_sock_str}"
        assert tcp_client_two_way.protocol_factory.full_name == f"TCP Client {server_sock_str}"
        assert tcp_client_two_way_two.protocol_factory.full_name == f"TCP Client {server_sock_str}_2"
        async with tcp_client_two_way as conn1, tcp_client_two_way_two as conn2:
            echo_response1 = await asyncio.wait_for(conn1.echo(), timeout=2)
            echo_response2 = await asyncio.wait_for(conn2.echo(), timeout=2)
            conn1.subscribe()
            conn2.subscribe()
            notification1 = await asyncio.wait_for(conn1.wait_notification(), timeout=2)
            notification2 = await asyncio.wait_for(conn2.wait_notification(), timeout=2)
        assert echo_response1 == echo_response2 == echo_response_object
        assert notification1 == notification2 == echo_notification_object

