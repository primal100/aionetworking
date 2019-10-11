import asyncio
import pytest
import json
import pickle
from pathlib import Path

from lib.formats.recording import get_recording_from_file
from lib.utils import alist


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, transport, adaptor, connections_manager,
                                           connection_is_stored):
        assert not transport.is_closing()
        assert connections_manager.total == 0
        assert connection.logger
        assert connection.transport is None
        connection.connection_made(transport)
        await connection.wait_connected()
        assert connection.is_connected()
        assert not transport.is_closing()
        assert connection._adaptor.context == adaptor.context
        assert connection._adaptor == adaptor
        assert connection.peer == f"tcp_{adaptor.context['peer']}"
        assert connection.logger is not None
        assert connection.transport == transport
        total_connections = 1 if connection_is_stored else 0
        assert connections_manager.total == total_connections
        if connection_is_stored:
            assert connections_manager.get(connection.peer) == connection
        connection.connection_lost(None)
        assert transport.is_closing()
        await connection.wait_closed()
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_send(self, connection, json_rpc_login_request_encoded, transport, queue, peer_data):
        connection.connection_made(transport)
        connection.send(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)

    @pytest.mark.asyncio
    async def test_02_send_data_adaptor_method(self, connection, json_rpc_login_request_encoded, transport, queue,
                                               peer_data):
        connection.connection_made(transport)
        connection.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)


class TestConnectionOneWayServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, tcp_protocol_one_way_server, json_rpc_login_request_encoded,
                                    json_rpc_logout_request_encoded, json_recording_data, json_codec,
                                    json_objects, tcp_transport):
        tcp_protocol_one_way_server.connection_made(tcp_transport)
        tcp_protocol_one_way_server.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1.2)
        tcp_protocol_one_way_server.data_received(json_rpc_logout_request_encoded)
        tcp_protocol_one_way_server.connection_lost(None)
        await asyncio.wait_for(tcp_protocol_one_way_server.wait_closed(), timeout=1)
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

    def test_01_is_child(self, tcp_protocol_one_way_server):
        assert tcp_protocol_one_way_server.is_child("TCP Server 127.0.0.1:8888")
        assert not tcp_protocol_one_way_server.is_child("UDP Server 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_02_pickle(self, tcp_protocol_one_way_server):
        data = pickle.dumps(tcp_protocol_one_way_server)
        protocol = pickle.loads(data)
        assert protocol == tcp_protocol_one_way_server


class TestConnectionOneWayClient:
    def test_00_is_child(self, tcp_protocol_one_way_client):
        assert tcp_protocol_one_way_client.is_child("TCP Client 127.0.0.1:0")
        assert not tcp_protocol_one_way_client.is_child("UDP Client 127.0.0.1:0")

    @pytest.mark.asyncio
    async def test_01_pickle(self, tcp_protocol_one_way_client):
        data = pickle.dumps(tcp_protocol_one_way_client)
        protocol = pickle.loads(data)
        assert protocol == tcp_protocol_one_way_client


class TestConnectionTwoWayServer:
    @pytest.mark.asyncio
    async def test_00_on_data_received(self, tmp_path, tcp_protocol_two_way_server, json_rpc_login_request_encoded,
                                       json_rpc_logout_request_encoded, json_rpc_login_response,
                                       json_rpc_logout_response, timestamp, json_recording, json_recording_data, queue,
                                       tcp_transport, peername):
        tcp_protocol_two_way_server.connection_made(tcp_transport)
        tcp_protocol_two_way_server.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1)
        tcp_protocol_two_way_server.data_received(json_rpc_logout_request_encoded)
        receiver1, msg1 = await asyncio.wait_for(queue.get(), 1)
        receiver2, msg2 = await asyncio.wait_for(queue.get(), 1)
        tcp_protocol_two_way_server.connection_lost(None)
        await tcp_protocol_two_way_server.close_wait()
        assert receiver1 == peername
        assert receiver2 == peername
        msgs = [json.loads(msg1), json.loads(msg2)]
        assert sorted(msgs, key=lambda x: x['id']) == sorted([json_rpc_login_response, json_rpc_logout_response],
                                                             key=lambda x: x['id'])
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == json_recording_data
        assert expected_file.read_bytes() == json_recording


class TestConnectionTwoWayClient:
    @pytest.mark.asyncio
    async def test_00_send_data_and_wait(self, tcp_protocol_two_way_client, json_rpc_login_request_encoded,
                                         json_rpc_login_request, tcp_transport_client,
                                         json_rpc_login_response_object, json_rpc_login_response_encoded, queue):
        tcp_protocol_two_way_client.connection_made(tcp_transport_client)
        task = asyncio.create_task(tcp_protocol_two_way_client.send_data_and_wait(1, json_rpc_login_request_encoded))
        receiver, msg = await queue.get()
        assert json.loads(msg) == json_rpc_login_request
        tcp_protocol_two_way_client.data_received(json_rpc_login_response_encoded)
        result = await asyncio.wait_for(task, timeout=1)
        json_rpc_login_response_object.context = result.context
        assert result == json_rpc_login_response_object
        tcp_protocol_two_way_client.connection_lost(None)
