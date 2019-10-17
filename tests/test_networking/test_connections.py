import asyncio
import pytest
import pickle
from pathlib import Path

from lib.networking.exceptions import MethodNotFoundError
from lib.formats.recording import get_recording_from_file
from lib.utils import alist


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, transport, adaptor, connections_manager,
                                           connection_is_stored, protocol_name):
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
        assert connection.peer == f"{protocol_name}_{adaptor.context['peer']}"
        assert connection.logger is not None
        assert connection.transport == transport
        total_connections = 1 if connection_is_stored else 0
        assert connections_manager.total == total_connections
        if connection_is_stored:
            assert connections_manager.get(connection.peer) == connection
        connection.close()
        assert transport.is_closing()
        await connection.wait_closed()
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_send(self, connection, json_rpc_login_request_encoded, transport, queue, peer_data):
        connection.connection_made(transport)
        transport.set_protocol(connection)
        connection.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)

    @pytest.mark.asyncio
    async def test_02_send_data_adaptor_method(self, connection, json_rpc_login_request_encoded, transport, queue,
                                               peer_data):
        connection.connection_made(transport)
        transport.set_protocol(connection)
        connection.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)


class TestConnectionOneWayServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, one_way_server_connection, json_rpc_login_request_encoded,
                                    json_rpc_logout_request_encoded, json_recording_data, json_codec, json_objects,
                                    one_way_server_transport):
        one_way_server_connection.connection_made(one_way_server_transport)
        one_way_server_transport.set_protocol(one_way_server_connection)
        one_way_server_connection.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1.2)
        one_way_server_connection.data_received(json_rpc_logout_request_encoded)
        one_way_server_connection.close()
        await asyncio.wait_for(one_way_server_connection.wait_closed(), timeout=1)
        expected_file = Path(tmp_path/'Data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects
        expected_file = Path(tmp_path / 'Recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist((get_recording_from_file(expected_file)))
        assert (packets[1].timestamp - packets[0].timestamp).total_seconds() > 1
        packets[0] = packets[0]._replace(timestamp=json_recording_data[0].timestamp)
        packets[1] = packets[1]._replace(timestamp=json_recording_data[1].timestamp)
        assert packets == json_recording_data

    def test_01_is_child(self, one_way_server_connection, one_way_server_protocol_name):
        assert one_way_server_connection.is_child(f"{one_way_server_protocol_name.upper()} Server 127.0.0.1:8888")
        assert not one_way_server_connection.is_child("ABC Server 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_02_pickle(self, one_way_server_connection):
        data = pickle.dumps(one_way_server_connection)
        protocol = pickle.loads(data)
        assert protocol == one_way_server_connection


class TestConnectionOneWayClient:
    def test_00_is_child(self, one_way_client_connection, one_way_client_protocol_name):
        assert one_way_client_connection.is_child(f"{one_way_client_protocol_name.upper()} Client 127.0.0.1:0")
        assert not one_way_client_connection.is_child("ABC Client 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_01_pickle(self, one_way_client_connection):
        data = pickle.dumps(one_way_client_connection)
        protocol = pickle.loads(data)
        assert protocol == one_way_client_connection


class TestConnectionTwoWayServer:
    @pytest.mark.asyncio
    async def test_00_on_data_received(self, tmp_path, two_way_server_connection, echo_encoded,
                                       echo_response_encoded,  timestamp, echo_recording_data, queue,
                                       two_way_server_transport, peername):
        two_way_server_connection.connection_made(two_way_server_transport)
        two_way_server_transport.set_protocol(two_way_server_connection)
        two_way_server_connection.data_received(echo_encoded)
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        two_way_server_connection.close()
        await asyncio.wait_for(two_way_server_connection.wait_closed(), timeout=1)
        assert receiver == peername
        assert msg == echo_response_encoded
        expected_file = Path(tmp_path / 'Recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist((get_recording_from_file(expected_file)))
        packets[0] = packets[0]._replace(timestamp=echo_recording_data[0].timestamp)
        assert packets == echo_recording_data

    @pytest.mark.asyncio
    async def test_01_on_data_received_notification(self, tmp_path, two_way_server_connection,
                                                    echo_notification_client_encoded, echo_notification_server_encoded,
                                                    timestamp, echo_recording_data, queue, two_way_server_transport, peername):
        two_way_server_connection.connection_made(two_way_server_transport)
        two_way_server_transport.set_protocol(two_way_server_connection)
        two_way_server_connection.data_received(echo_notification_client_encoded)
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        two_way_server_connection.close()
        await asyncio.wait_for(two_way_server_connection.wait_closed(), timeout=1)
        assert receiver == peername
        assert msg == echo_notification_server_encoded
        expected_file = Path(tmp_path / 'Recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist((get_recording_from_file(expected_file)))
        assert len(packets) == 1


class TestConnectionTwoWayClient:
    @pytest.mark.asyncio
    async def test_00_send_data_and_wait(self, two_way_client_connection, echo_encoded, echo_response_encoded,
                                         echo_response_object, two_way_client_transport, queue):
        two_way_client_connection.connection_made(two_way_client_transport)
        two_way_client_transport.set_protocol(two_way_client_connection)
        task = asyncio.create_task(two_way_client_connection.send_data_and_wait(1, echo_encoded))
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_encoded
        two_way_client_connection.data_received(echo_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_01_send_notification_and_wait(self, two_way_client_connection, echo_notification_client_encoded,
                                                 echo_notification_server_encoded, echo_notification_object,
                                                 two_way_client_transport, queue):
        two_way_client_connection.connection_made(two_way_client_transport)
        two_way_client_transport.set_protocol(two_way_client_connection)
        two_way_client_connection.send_data(echo_notification_client_encoded)
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_notification_client_encoded
        two_way_client_connection.data_received(echo_notification_server_encoded)
        result = await asyncio.wait_for(two_way_client_connection.wait_notification(), timeout=1)
        assert result == echo_notification_object

    @pytest.mark.asyncio
    async def test_02_requester(self, two_way_client_connection, echo_encoded, echo_response_encoded,
                                echo_response_object, two_way_client_transport, queue):
        two_way_client_connection.connection_made(two_way_client_transport)
        two_way_client_transport.set_protocol(two_way_client_connection)
        task = asyncio.create_task(two_way_client_connection.echo())
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_encoded
        two_way_client_connection.data_received(echo_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        assert result == echo_response_object

    @pytest.mark.asyncio
    async def test_03_requester_notification(self, two_way_client_connection, echo_notification_client_encoded,
                                             echo_notification_server_encoded, echo_notification_object,
                                             two_way_client_transport, queue):
        two_way_client_connection.connection_made(two_way_client_transport)
        two_way_client_transport.set_protocol(two_way_client_connection)
        two_way_client_connection.subscribe()
        receiver, msg = await asyncio.wait_for(queue.get(), timeout=1)
        assert msg == echo_notification_client_encoded
        two_way_client_connection.data_received(echo_notification_server_encoded)
        result = await asyncio.wait_for(two_way_client_connection.wait_notification(), timeout=1)
        assert result == echo_notification_object

    @pytest.mark.asyncio
    async def test_04_no_method(self, two_way_client_connection, two_way_client_transport):
        two_way_client_connection.connection_made(two_way_client_transport)
        two_way_client_transport.set_protocol(two_way_client_connection)
        with pytest.raises(MethodNotFoundError):
            two_way_client_connection.ech()