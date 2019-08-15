import asyncio
import pytest
import json
import pickle
from pathlib import Path

from lib.utils import alist, Record


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, transport, adaptor, connections_manager, connection_is_stored):
        assert not transport.is_closing()
        assert connections_manager.total == 0
        assert connection.logger
        assert connection.transport is None
        connection.connection_made(transport)
        await connection.wait_connected()
        assert connection.is_connected()
        assert not transport.is_closing()
        assert connection.adaptor.context == adaptor.context
        assert connection.adaptor == adaptor
        assert connection.peer == f"tcp_{adaptor.context['peer']}"
        assert connection.logger is not None
        assert connection.transport == transport
        total_connections = 1 if connection_is_stored else 0
        assert connections_manager.total == total_connections
        if connection_is_stored:
            assert connections_manager.get(connection.peer) == connection
        connection.connection_lost(None)
        await connection.close_wait()
        assert connections_manager.total == 0
        assert transport.is_closing()

    @pytest.mark.asyncio
    async def test_01_send(self, connection, asn_one_encoded, transport, queue, peer_data):
        connection.connection_made(transport)
        connection.send(asn_one_encoded)
        assert queue.get_nowait() == (peer_data, asn_one_encoded)
        connection.connection_lost(None)
        await connection.close_wait()

    @pytest.mark.asyncio
    async def test_02_send_data_adaptor_method(self, connection, asn_one_encoded, transport, queue, peer_data):
        connection.connection_made(transport)
        connection.send_data(asn_one_encoded)
        assert queue.get_nowait() == (peer_data, asn_one_encoded)
        connection.connection_lost(None)
        await connection.close_wait()


class TestConnectionOneWayServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, tcp_protocol_one_way_server, buffer_asn1_1, buffer_asn1_2,
                                    asn1_recording, asn1_recording_data, asn_codec, asn_buffer,
                                    asn_objects, tcp_transport, buffered_file_storage_pre_action_binary,
                                    buffered_file_storage_action_binary):
        tcp_protocol_one_way_server.connection_made(tcp_transport)
        await tcp_protocol_one_way_server.wait_connected()
        tcp_protocol_one_way_server.data_received(buffer_asn1_1)
        await asyncio.sleep(1)
        tcp_protocol_one_way_server.data_received(buffer_asn1_2)
        tcp_protocol_one_way_server.connection_lost(None)
        await tcp_protocol_one_way_server.close_wait()
        await asyncio.wait(
            [buffered_file_storage_action_binary.close(), buffered_file_storage_pre_action_binary.close()], timeout=2)
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = await alist(asn_codec.from_file(expected_file))
        assert msgs == asn_objects
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn1_recording
        packets = list(Record.from_file(expected_file))
        assert packets == asn1_recording_data

    def test_01_is_child(self, tcp_protocol_one_way_server):
        assert tcp_protocol_one_way_server.is_child("TCP Server 127.0.0.1:8888")
        assert not tcp_protocol_one_way_server.is_child("UDP Server 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_02_pickle(self, tcp_protocol_one_way_server):
        data = pickle.dumps(tcp_protocol_one_way_server)
        protocol = pickle.loads(data)
        assert protocol == tcp_protocol_one_way_server


class TestConnectionOneWayClient:
    @pytest.mark.asyncio
    async def test_00_pickle(self, tcp_protocol_one_way_client):
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
