import asyncio
import pytest


async def wait_connections_closed(server_started, client_connected, connection_type):
    if connection_type == 'udp':
        await asyncio.sleep(0.1)  # Workaround for bpo-38471
    await asyncio.wait_for(client_connected.close(), 300)
    if connection_type == 'udp':
        server_started.close_all_connections()
    await asyncio.wait_for(server_started.wait_num_has_connected(1), 3)
    await asyncio.wait_for(server_started.wait_num_connections(0), 1)
    await asyncio.wait_for(server_started.wait_all_tasks_done(), 3)


@pytest.mark.connections('allplus_oneway_all')
class TestOneWayServer:

    @pytest.mark.asyncio
    async def test_00_send(self, server_started, client_connected, client_connection_started, json_decoded_multi,
                           assert_server_buffered_file_storage_ok, fixed_timestamp, connection_type):
        client_connection_started.encode_and_send_msgs(json_decoded_multi)
        await wait_connections_closed(server_started, client_connected, connection_type)
        await asyncio.wait_for(assert_server_buffered_file_storage_ok, 1)

    @pytest.mark.asyncio
    async def test_01_send_recording(self, server_started, client_connected,  client_connection_started,
                                     assert_server_buffered_file_storage_ok, recordings_file_with_data, fixed_timestamp,
                                     connection_type):
        await client_connection_started.play_recording(recordings_file_with_data)
        await wait_connections_closed(server_started, client_connected, connection_type)
        await asyncio.wait_for(assert_server_buffered_file_storage_ok, 2)


@pytest.mark.connections('all_twoway_all')
class TestTwoWayServer:
    @pytest.mark.asyncio
    async def test_00_send(self, server_started, client_connected, client_connection_started, echo_response_object,
                           echo_exception_response_object, echo_notification_object, fixed_timestamp):
        echo_response = await client_connection_started.echo()
        client_connection_started.subscribe()
        notification = await client_connection_started.wait_notification()
        assert echo_response == echo_response_object
        assert notification == echo_notification_object

    @pytest.mark.asyncio
    async def test_01_send_multiple_senders(self, reset_endpoint_names, server_started, client, actual_server_sock,
                                            client_two, echo_response_object, echo_exception_response_object,
                                            echo_notification_object):
        async with client as conn1, client_two as conn2:
            echo_response1 = await asyncio.wait_for(conn1.echo(), timeout=2)
            echo_response2 = await asyncio.wait_for(conn2.echo(), timeout=2)
            conn1.subscribe()
            conn2.subscribe()
            notification1 = await asyncio.wait_for(conn1.wait_notification(), timeout=2)
            notification2 = await asyncio.wait_for(conn2.wait_notification(), timeout=2)
        assert echo_response1 == echo_response2 == echo_response_object
        assert notification1 == notification2 == echo_notification_object

