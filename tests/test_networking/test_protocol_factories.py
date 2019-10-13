import asyncio
import pytest
import pickle
from pathlib import Path
from lib.utils import addr_tuple_to_str, alist


class TestStreamProtocolFactories:

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


class TestOneWayServerDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_one_way_server, udp_protocol_one_way_server,
                                           json_rpc_logout_request_encoded, udp_transport_server, peername,
                                           json_rpc_login_request_encoded, connections_manager, tmp_path, json_codec,
                                           json_objects):
        protocol_factory = udp_protocol_factory_one_way_server()
        assert protocol_factory == udp_protocol_factory_one_way_server
        protocol_factory.connection_made(udp_transport_server)
        udp_transport_server.set_protocol(protocol_factory)
        protocol_factory.datagram_received(json_rpc_login_request_encoded, peername)
        assert connections_manager.total == 1
        await asyncio.wait_for(udp_protocol_factory_one_way_server.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{addr_tuple_to_str(peername)}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert udp_protocol_factory_one_way_server.logger == new_connection.logger
        assert udp_protocol_factory_one_way_server.is_owner(new_connection)
        protocol_factory.datagram_received(json_rpc_logout_request_encoded, peername)
        assert connections_manager.total == 1
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0
        expected_file = Path(tmp_path / 'Data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_one_way_server):
        data = pickle.dumps(udp_protocol_factory_one_way_server)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_one_way_server


class TestOneWayClientDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_one_way_client, udp_protocol_one_way_client,
                                           json_rpc_login_request_encoded, udp_transport_client,
                                           sock, connections_manager, queue):
        protocol_factory = udp_protocol_factory_one_way_client()
        assert protocol_factory == udp_protocol_factory_one_way_client
        protocol_factory.connection_made(udp_transport_client)
        udp_transport_client.set_protocol(protocol_factory)
        conn = protocol_factory.new_peer()
        assert connections_manager.total == 1
        full_peername = f"udp_{addr_tuple_to_str(sock)}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        conn.send(json_rpc_login_request_encoded)
        msg = await queue.get()
        assert msg == (sock, json_rpc_login_request_encoded)
        assert udp_protocol_factory_one_way_client.logger == new_connection.logger
        assert udp_protocol_factory_one_way_client.is_owner(new_connection)
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_one_way_client):
        data = pickle.dumps(udp_protocol_factory_one_way_client)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_one_way_client


class TestTwoWayServerDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_two_way_server, udp_protocol_two_way_server,
                                           echo_encoded, udp_transport_server, echo_response_encoded, peername,
                                           connections_manager, queue):
        protocol_factory = udp_protocol_factory_two_way_server()
        assert protocol_factory == udp_protocol_factory_two_way_server
        protocol_factory.connection_made(udp_transport_server)
        udp_transport_server.set_protocol(protocol_factory)
        protocol_factory.datagram_received(echo_encoded, peername)
        assert connections_manager.total == 1
        await asyncio.wait_for(udp_protocol_factory_two_way_server.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{addr_tuple_to_str(peername)}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert udp_protocol_factory_two_way_server.logger == new_connection.logger
        assert udp_protocol_factory_two_way_server.is_owner(new_connection)
        msg = await queue.get()
        assert msg == (peername, echo_response_encoded)
        protocol_factory.datagram_received(echo_encoded, peername)
        msg = await queue.get()
        assert msg == (peername, echo_response_encoded)
        assert connections_manager.total == 1
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_two_way_server):
        data = pickle.dumps(udp_protocol_factory_two_way_server)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_two_way_server


class TestTwoWayClientDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_two_way_client, udp_protocol_two_way_client,
                                           echo_response_encoded, udp_transport_client, echo_encoded, sock,
                                           connections_manager, queue, echo_response_object):
        protocol_factory = udp_protocol_factory_two_way_client()
        assert protocol_factory == udp_protocol_factory_two_way_client
        protocol_factory.connection_made(udp_transport_client)
        udp_transport_client.set_protocol(protocol_factory)
        conn = protocol_factory.new_peer()
        assert connections_manager.total == 1
        task = asyncio.create_task(conn.echo())
        msg = await queue.get()
        assert msg == (sock, echo_encoded)
        protocol_factory.datagram_received(echo_response_encoded, sock)
        response = await asyncio.wait_for(task, timeout=1)
        assert response == echo_response_object
        assert connections_manager.total == 1
        full_peername = f"udp_{addr_tuple_to_str(sock)}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert udp_protocol_factory_two_way_client.logger == new_connection.logger
        assert udp_protocol_factory_two_way_client.is_owner(new_connection)
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_two_way_client):
        data = pickle.dumps(udp_protocol_factory_two_way_client)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_two_way_client
