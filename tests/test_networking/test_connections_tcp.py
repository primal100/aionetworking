import asyncio
import pytest
import json
from pathlib import Path

from lib.utils import alist, addr_str_to_tuple, Record


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, transport, adaptor, connections_manager):
        assert not transport.is_closing()
        assert connections_manager.total == 0
        assert connection.logger
        assert connection.transport is None
        connection.connection_made(transport)
        assert not transport.is_closing()
        assert connection.adaptor == adaptor
        assert connection.peer_str == adaptor.context['peer']
        assert connection.peer == addr_str_to_tuple(adaptor.context['peer'])
        assert connection.sock == addr_str_to_tuple(adaptor.context['sock'])
        assert connection.alias == adaptor.context['alias']
        assert connection.logger is not None
        assert connection.transport == transport
        assert connections_manager.total == 1
        assert connections_manager.get(connection.peer_str) == connection
        connection.connection_lost(None)
        await connection.close_wait()
        assert connections_manager.total == 0
        assert transport.is_closing()

    def test_01_clone(self, connection):
        connection_cloned = connection.clone(parent_id=5)
        assert connection_cloned.parent_id == 5
        connection.parent_id = 5
        assert connection_cloned == connection

    def test_02_is_child(self, connection):
        assert connection.is_child(4)
        assert not connection.is_child(5)


class TestConnectionOneWayServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, tcp_protocol_one_way_server, asn_buffer, buffer_asn1_1,
                                    buffer_asn1_2, asn1_recording, asn1_recording_data, asn_codec,
                                    asn_objects, tcp_transport):
        tcp_protocol_one_way_server.connection_made(tcp_transport)
        tcp_protocol_one_way_server.data_received(buffer_asn1_1)
        await asyncio.sleep(1)
        tcp_protocol_one_way_server.data_received(buffer_asn1_2)
        tcp_protocol_one_way_server.connection_lost(None)
        await tcp_protocol_one_way_server.close_wait()
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


class TestConnectionSenderOneWay:
    @pytest.mark.asyncio
    async def test_00_send(self, tcp_protocol_one_way_client, asn_one_encoded, tcp_transport_client, deque, sock):
        tcp_protocol_one_way_client.connection_made(tcp_transport_client)
        tcp_protocol_one_way_client.send(asn_one_encoded)
        assert deque.pop() == (sock, asn_one_encoded)
        tcp_protocol_one_way_client.connection_lost(None)
        await tcp_protocol_one_way_client.close_wait()

    @pytest.mark.asyncio
    async def test_01_send_data_adaptor_method(self, tcp_protocol_one_way_client, asn_one_encoded, tcp_transport_client, deque, sock):
        tcp_protocol_one_way_client.connection_made(tcp_transport_client)
        tcp_protocol_one_way_client.send_data(asn_one_encoded)
        assert deque.pop() == (sock, asn_one_encoded)
        tcp_protocol_one_way_client.connection_lost(None)
        await tcp_protocol_one_way_client.close_wait()


class TestConnectionTwoWayServer:
    @pytest.mark.asyncio
    async def test_00_on_data_received(self, tmp_path, tcp_protocol_two_way_server, json_rpc_login_request_encoded,
                                       json_rpc_logout_request_encoded, json_rpc_login_response,
                                       json_rpc_logout_response, timestamp, json_recording, json_recording_data, queue,
                                       tcp_transport):
        tcp_protocol_two_way_server.connection_made(tcp_transport)
        tcp_protocol_two_way_server.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1)
        tcp_protocol_two_way_server.data_received(json_rpc_logout_request_encoded)
        msg1 = await asyncio.wait_for(queue.get(), 1)
        msg2 = await asyncio.wait_for(queue.get(), 1)
        tcp_protocol_two_way_server.connection_lost(None)
        await tcp_protocol_two_way_server.close_wait()
        msgs = [json.loads(msg1[1]), json.loads(msg2[1])]
        assert sorted(msgs, key=lambda x: x['id']) == sorted([json_rpc_login_response, json_rpc_logout_response],
                                                             key=lambda x: x['id'])
        expected_file = Path(tmp_path / '127.0.0.1.recording')
        assert expected_file.exists()
        packets = list(Record.from_file(expected_file))
        assert packets == json_recording_data
        assert expected_file.read_bytes() == json_recording


class TestConnectionTwoWayClient:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, tcp_protocol_one_way_server, asn_buffer, buffer_asn1_1,
                                    buffer_asn1_2, asn1_recording, asn1_recording_data, asn_codec,
                                    asn_objects, tcp_transport):
        tcp_protocol_one_way_server.connection_made(tcp_transport)
        tcp_protocol_one_way_server.data_received(buffer_asn1_1)
        await asyncio.sleep(1)
        tcp_protocol_one_way_server.data_received(buffer_asn1_2)
        tcp_protocol_one_way_server.connection_lost(None)
        await tcp_protocol_one_way_server.close_wait()
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
