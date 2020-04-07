import asyncio
import pytest
import pickle

from aionetworking.networking.exceptions import MethodNotFoundError, MessageFromNotAuthorizedHost


@pytest.mark.connections()
class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, transport, adaptor, connections_manager, connection_type):
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
        assert connection.peer == f"{connection_type}_{adaptor.context['own']}_{adaptor.context['peer']}"
        assert connection.logger is not None
        assert connection.transport == transport
        assert connections_manager.total == 1
        assert connections_manager.get(connection.peer) == connection
        connection.close()
        assert transport.is_closing()
        await connection.wait_closed()
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_send(self, connection_connected, json_rpc_login_request_encoded, queue, peer):
        connection_connected.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer, json_rpc_login_request_encoded)

    @pytest.mark.asyncio
    async def test_02_send_data_adaptor_method(self, connection_connected, json_rpc_login_request_encoded, transport, queue,
                                               peer):
        connection_connected.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer, json_rpc_login_request_encoded)

    def test_03_is_child(self, connection, parent_name):
        assert connection.is_child(parent_name)
        assert not connection.is_child(f"ABC Server")

    @pytest.mark.asyncio
    async def test_04_pickle(self, connection):
        data = pickle.dumps(connection)
        protocol = pickle.loads(data)
        assert protocol == connection


@pytest.mark.skip
class TestConnectionAllowedSenders:
    @pytest.mark.asyncio
    async def test_00_sender_valid_ipv4_ok(self, tcp_protocol_two_way_server_allowed_senders, client_sock):
        assert tcp_protocol_two_way_server_allowed_senders._sender_valid(client_sock[0], client_sock[0]) is True

    @pytest.mark.asyncio
    async def test_01_sender_valid_ipv6_ok(self, tcp_protocol_two_way_server_allowed_senders, client_sock_ipv6):
        assert tcp_protocol_two_way_server_allowed_senders._sender_valid(client_sock_ipv6[0], client_sock_ipv6[0]) is True

    @pytest.mark.asyncio
    async def test_02_sender_valid_hostname_ok(self, tcp_protocol_two_way_server_allowed_senders_hostname, client_hostname):
        assert tcp_protocol_two_way_server_allowed_senders_hostname._sender_valid('10.10.10.10', client_hostname) is True

    @pytest.mark.asyncio
    async def test_03_sender_valid_ipv4_not_ok(self, tcp_protocol_two_way_server_allowed_senders):
        assert tcp_protocol_two_way_server_allowed_senders._sender_valid('127.0.0.2', 'abcd') is False

    @pytest.mark.asyncio
    async def test_04_sender_valid_ipv6_not_ok(self, tcp_protocol_two_way_server_allowed_senders):
        assert tcp_protocol_two_way_server_allowed_senders._sender_valid('::2', 'abcd') is False

    @pytest.mark.asyncio
    async def test_05_check_peer_ipv4_ok(self, tcp_protocol_two_way_server_allowed_senders, client_sock):
        tcp_protocol_two_way_server_allowed_senders.context['address'] = client_sock[0]
        tcp_protocol_two_way_server_allowed_senders.context['host'] = 'abcd'
        tcp_protocol_two_way_server_allowed_senders._check_peer()

    @pytest.mark.asyncio
    async def test_06_check_peer_ipv6_ok(self, tcp_protocol_two_way_server_allowed_senders, client_sock_ipv6):
        tcp_protocol_two_way_server_allowed_senders.context['address'] = client_sock_ipv6[0]
        tcp_protocol_two_way_server_allowed_senders.context['host'] = 'abcd'
        tcp_protocol_two_way_server_allowed_senders._check_peer()

    @pytest.mark.asyncio
    async def test_07_check_peer_hostname_ok(self, tcp_protocol_two_way_server_allowed_senders_hostname, client_hostname):
        tcp_protocol_two_way_server_allowed_senders_hostname.context['address'] = '10.10.10.10'
        tcp_protocol_two_way_server_allowed_senders_hostname.context['host'] = client_hostname
        tcp_protocol_two_way_server_allowed_senders_hostname._check_peer()

    @pytest.mark.asyncio
    async def test_08_check_peer_ipv4_not_ok(self, tcp_protocol_two_way_server_allowed_senders):
        tcp_protocol_two_way_server_allowed_senders.context['address'] = '127.0.0.2'
        tcp_protocol_two_way_server_allowed_senders.context['host'] = 'abcd'
        with pytest.raises(MessageFromNotAuthorizedHost):
            tcp_protocol_two_way_server_allowed_senders._check_peer()

    @pytest.mark.asyncio
    async def test_09_check_peer_ipv6_not_ok(self, tcp_protocol_two_way_server_allowed_senders):
        tcp_protocol_two_way_server_allowed_senders.context['address'] = '::2'
        tcp_protocol_two_way_server_allowed_senders.context['host'] = 'abcd'
        with pytest.raises(MessageFromNotAuthorizedHost):
            tcp_protocol_two_way_server_allowed_senders._check_peer()

    @pytest.mark.asyncio
    async def test_13_check_peer_hostname_not_ok(self, tcp_protocol_two_way_server_allowed_senders_hostname):
        tcp_protocol_two_way_server_allowed_senders_hostname.context['peer'] = '10.10.10.10:11111'
        tcp_protocol_two_way_server_allowed_senders_hostname.context['address'] = '10.10.10.10'
        tcp_protocol_two_way_server_allowed_senders_hostname.context['host'] = 'abcd'
        with pytest.raises(MessageFromNotAuthorizedHost):
            tcp_protocol_two_way_server_allowed_senders_hostname._check_peer()


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
    async def test_00_send_data_and_wait(self, connection_connected, echo_encoded, echo_response_encoded, echo_response_object,
                                         transport, queue):
        task = asyncio.create_task(connection_connected.send_data_and_wait(1, echo_encoded))
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_encoded
        connection_connected.data_received(echo_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_01_send_notification_and_wait(self, connection_connected, echo_notification_client_encoded, transport,
                                                 echo_notification_server_encoded, echo_notification_object,
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
        task = asyncio.create_task(connection_connected.echo())
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
