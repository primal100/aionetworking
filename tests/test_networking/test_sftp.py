import asyncio
import pytest
import pickle
from pathlib import Path

from lib.networking.exceptions import MethodNotFoundError
from lib.formats.recording import get_recording_from_file
from lib.utils import alist


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, sftp_conn, adaptor, connections_manager,
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

    @pytest.mark.asyncio
    async def test_00_send(self, connection, json_rpc_login_request_encoded, transport, queue, peer_data):
        connection.connection_made(transport)
        transport.set_protocol(connection)
        connection.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)

    @pytest.mark.asyncio
    async def test_01_send_data_adaptor_method(self, connection, json_rpc_login_request_encoded, transport, queue,
                                               peer_data):
        connection.connection_made(transport)
        transport.set_protocol(connection)
        connection.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)

    def test_02_is_child(self, one_way_client_connection, one_way_client_protocol_name):
        assert one_way_client_connection.is_child(f"{one_way_client_protocol_name.upper()} Client 127.0.0.1:0")
        assert not one_way_client_connection.is_child("ABC Client 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_03_pickle(self, one_way_client_connection):
        data = pickle.dumps(one_way_client_connection)
        protocol = pickle.loads(data)
        assert protocol == one_way_client_connection


class TestSFTPProtocolFactories:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, stream_protocol_factory, stream_connection, stream_transport,
                                           stream_connection_is_stored):
        new_connection = stream_protocol_factory()
        assert stream_protocol_factory.logger == new_connection.logger
        assert new_connection == stream_connection
        assert stream_protocol_factory.is_owner(new_connection)
        new_connection.connection_made(stream_transport)
        new_connection.transport.set_protocol(new_connection)
        if stream_connection_is_stored:
            await asyncio.wait_for(stream_protocol_factory.wait_num_connected(1), timeout=1)
        await asyncio.wait_for(new_connection.wait_connected(), timeout=1)
        new_connection.transport.close()
        await asyncio.wait_for(stream_protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, stream_protocol_factory):
        data = pickle.dumps(stream_protocol_factory)
        factory = pickle.loads(data)
        assert factory == stream_protocol_factory
        await stream_protocol_factory.close()