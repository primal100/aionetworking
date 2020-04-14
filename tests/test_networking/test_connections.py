import asyncio
import pytest
import pickle

from aionetworking.compatibility import create_task
from aionetworking.networking.exceptions import MethodNotFoundError, MessageFromNotAuthorizedHost


@pytest.mark.connections()
class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, transport, adaptor, connections_manager, peer_prefix):
        assert not transport.is_closing()
        assert connections_manager.total == 0
        assert connection.logger
        assert connection.transport is None
        connection.connection_made(transport)
        transport.set_protocol(connection)
        await connection.wait_connected()
        assert connection.is_connected()
        assert not transport.is_closing()
        assert connection._adaptor.context == adaptor.context
        assert connection._adaptor == adaptor
        assert connection.peer == f"{peer_prefix}_{adaptor.context['own']}_{adaptor.context['peer']}"
        assert connection.logger is not None
        assert connection.transport == transport
        assert connections_manager.total == 1
        assert connections_manager.get(connection.peer) == connection
        connection.close()
        await asyncio.wait_for(connection.wait_closed(), 2)
        assert transport.is_closing()
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_send(self, connection_connected, json_rpc_login_request_encoded, queue, peer):
        connection_connected.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer, json_rpc_login_request_encoded)

    @pytest.mark.asyncio
    async def test_02_send_data_adaptor_method(self, connection_connected, json_rpc_login_request_encoded, transport,
                                               queue, peer):
        connection_connected.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer, json_rpc_login_request_encoded)

    def test_03_is_child(self, connection, parent_name):
        assert connection.is_child(parent_name)
        assert not connection.is_child(f"ABC Server")

    def test_04_pickle(self, connection):
        data = pickle.dumps(connection)
        protocol = pickle.loads(data)
        assert protocol == connection


@pytest.mark.connections('all_oneway_server')
class TestConnectionOneWayServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, connection_connected, json_rpc_login_request_encoded, transport,
                                    fixed_timestamp, json_rpc_logout_request_encoded, assert_recordings_ok,
                                    assert_buffered_file_storage_ok):
        connection_connected.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1.2)
        connection_connected.data_received(json_rpc_logout_request_encoded)
        connection_connected.close()
        await asyncio.wait_for(connection_connected.wait_closed(), timeout=1)
        await assert_buffered_file_storage_ok
        await assert_recordings_ok


@pytest.mark.connections('all_twoway_server')
class TestConnectionTwoWayServer:
    @pytest.mark.asyncio
    async def test_00_on_data_received(self, connection_connected, echo_encoded, echo_response_encoded, fixed_timestamp,
                                       queue, peer, assert_recordings_ok):
        connection_connected.data_received(echo_encoded)
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        connection_connected.close()
        await asyncio.wait_for(connection_connected.wait_closed(), timeout=1)
        assert receiver == peer
        assert msg == echo_response_encoded
        await assert_recordings_ok

    @pytest.mark.asyncio
    async def test_01_on_data_received_notification(self, connection_connected, peer, fixed_timestamp, queue,
                                                    echo_notification_client_encoded, echo_notification_server_encoded):
        connection_connected.data_received(echo_notification_client_encoded)
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        connection_connected.close()
        await asyncio.wait_for(connection_connected.wait_closed(), timeout=1)
        assert receiver == peer
        assert msg == echo_notification_server_encoded


@pytest.mark.connections('all_twoway_client')
class TestConnectionTwoWayClient:
    @pytest.mark.asyncio
    async def test_00_send_data_and_wait(self, connection_connected, echo_encoded, echo_response_encoded,
                                         echo_response_object, transport, queue):
        task = create_task(connection_connected.send_data_and_wait(1, echo_encoded))
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_encoded
        connection_connected.data_received(echo_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_01_send_notification_and_wait(self, connection_connected, echo_notification_client_encoded,
                                                 transport, echo_notification_server_encoded, echo_notification_object,
                                                 queue):
        connection_connected.send_data(echo_notification_client_encoded)
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_notification_client_encoded
        connection_connected.data_received(echo_notification_server_encoded)
        result = await asyncio.wait_for(connection_connected.wait_notification(), timeout=1)
        assert result == echo_notification_object

    @pytest.mark.asyncio
    async def test_02_requester(self, connection_connected, echo_encoded, echo_response_encoded, echo_response_object,
                                queue):
        task = create_task(connection_connected.echo())
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_encoded
        connection_connected.data_received(echo_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_03_requester_notification(self, connection_connected, echo_notification_client_encoded,
                                             echo_notification_server_encoded, echo_notification_object, queue):
        connection_connected.subscribe()
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_notification_client_encoded
        connection_connected.data_received(echo_notification_server_encoded)
        result = await asyncio.wait_for(connection_connected.wait_notification(), timeout=1)
        assert result == echo_notification_object

    @pytest.mark.asyncio
    async def test_04_no_method(self, connection_connected, transport):
        with pytest.raises(MethodNotFoundError):
            connection_connected.ech()


class TestConnectionAllowedSenders:
    @pytest.mark.asyncio
    async def test_00_sender_valid_ok(self, connection_allowed_senders, allowed_sender):
        assert connection_allowed_senders._sender_valid(*allowed_sender) is True

    @pytest.mark.asyncio
    async def test_01_sender_valid_not_ok(self, connection_allowed_senders, incorrect_allowed_sender):
        assert connection_allowed_senders._sender_valid(*incorrect_allowed_sender) is False

    @pytest.mark.asyncio
    async def test_02_check_peer_ok(self, connection_allowed_senders, allowed_sender):
        connection_allowed_senders.context['address'] = allowed_sender[0]
        connection_allowed_senders.context['host'] = allowed_sender[1]
        connection_allowed_senders._check_peer()

    @pytest.mark.asyncio
    async def test_03_check_peer_not_ok(self, connection_allowed_senders, incorrect_allowed_sender):
        connection_allowed_senders.context['address'] = incorrect_allowed_sender[0]
        connection_allowed_senders.context['host'] = incorrect_allowed_sender[1]
        with pytest.raises(MessageFromNotAuthorizedHost):
            connection_allowed_senders._check_peer()
