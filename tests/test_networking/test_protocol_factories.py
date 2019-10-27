import asyncio
import pytest
import pickle
from pathlib import Path
from lib.utils import addr_tuple_to_str, alist


class TestStreamProtocolFactories:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, stream_protocol_factory, stream_connection, stream_transport):
        new_connection = stream_protocol_factory()
        assert stream_protocol_factory.logger == new_connection.logger
        assert new_connection == stream_connection
        assert stream_protocol_factory.is_owner(new_connection)
        new_connection.connection_made(stream_transport)
        new_connection.transport.set_protocol(new_connection)
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

    @pytest.mark.asyncio
    async def test_02_protocol_factory_custom_codec_config(self, protocol_factory_one_way_server_codec_kwargs,
                                                           tcp_transport, json_codec_with_kwargs):
        new_connection = protocol_factory_one_way_server_codec_kwargs()
        assert new_connection.codec_config == {'test_param': 'abc'}
        new_connection.connection_made(tcp_transport)
        tcp_transport.set_protocol(new_connection)
        adaptor = new_connection._adaptor
        assert adaptor.codec_config == {'test_param': 'abc'}
        assert adaptor.codec.msg_obj == json_codec_with_kwargs.msg_obj
        assert adaptor.codec.test_param == json_codec_with_kwargs.test_param
        tcp_transport.close()


class TestOneWayServerDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_one_way_server_started, udp_protocol_one_way_server,
                                           json_rpc_logout_request_encoded, udp_transport_server, peer, sock,
                                           json_rpc_login_request_encoded, connections_manager, tmp_path, json_codec,
                                           json_objects, peer_str, sock_str):
        protocol_factory = udp_protocol_factory_one_way_server_started()
        assert protocol_factory == udp_protocol_factory_one_way_server_started
        protocol_factory.connection_made(udp_transport_server)
        udp_transport_server.set_protocol(protocol_factory)
        protocol_factory.datagram_received(json_rpc_login_request_encoded, peer)
        assert connections_manager.total == 1
        await asyncio.wait_for(udp_protocol_factory_one_way_server_started.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{sock_str}_{peer_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert udp_protocol_factory_one_way_server_started.logger == new_connection.logger
        assert udp_protocol_factory_one_way_server_started.is_owner(new_connection)
        protocol_factory.datagram_received(json_rpc_logout_request_encoded, peer)
        assert connections_manager.total == 1
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        udp_transport_server.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0
        expected_file = Path(tmp_path / 'data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_one_way_server_started):
        data = pickle.dumps(udp_protocol_factory_one_way_server_started)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_one_way_server_started


class TestOneWayClientDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_one_way_client_started, udp_protocol_one_way_client,
                                           json_rpc_login_request_encoded, udp_transport_client, peer, peer_str, sock_str,
                                           sock, connections_manager, queue):
        protocol_factory = udp_protocol_factory_one_way_client_started()
        assert protocol_factory == udp_protocol_factory_one_way_client_started
        protocol_factory.connection_made(udp_transport_client)
        udp_transport_client.set_protocol(protocol_factory)
        conn = protocol_factory.new_peer()
        assert connections_manager.total == 1
        full_peername = f"udp_{peer_str}_{sock_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        conn.send(json_rpc_login_request_encoded)
        msg = await queue.get()
        assert msg == (sock, json_rpc_login_request_encoded)
        assert udp_protocol_factory_one_way_client_started.logger == new_connection.logger
        assert udp_protocol_factory_one_way_client_started.is_owner(new_connection)
        udp_transport_client.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_one_way_client_started):
        data = pickle.dumps(udp_protocol_factory_one_way_client_started)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_one_way_client_started


class TestTwoWayServerDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_two_way_server_started,
                                           udp_protocol_two_way_server, sock, peer_str, sock_str,
                                           echo_encoded, udp_transport_server, echo_response_encoded, peer,
                                           connections_manager, queue):
        protocol_factory = udp_protocol_factory_two_way_server_started()
        assert protocol_factory == udp_protocol_factory_two_way_server_started
        protocol_factory.connection_made(udp_transport_server)
        udp_transport_server.set_protocol(protocol_factory)
        protocol_factory.datagram_received(echo_encoded, peer)
        assert connections_manager.total == 1
        await asyncio.wait_for(udp_protocol_factory_two_way_server_started.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{sock_str}_{peer_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert udp_protocol_factory_two_way_server_started.logger == new_connection.logger
        assert udp_protocol_factory_two_way_server_started.is_owner(new_connection)
        msg = await queue.get()
        assert msg == (peer, echo_response_encoded)
        protocol_factory.datagram_received(echo_encoded, peer)
        msg = await queue.get()
        assert msg == (peer, echo_response_encoded)
        assert connections_manager.total == 1
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        udp_transport_server.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_two_way_server_started):
        data = pickle.dumps(udp_protocol_factory_two_way_server_started)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_two_way_server_started


class TestTwoWayClientDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, udp_protocol_factory_two_way_client_started, udp_protocol_two_way_client,
                                           echo_response_encoded, udp_transport_client, echo_encoded, sock, peer,
                                           connections_manager, queue, echo_response_object, peer_str, sock_str):
        protocol_factory = udp_protocol_factory_two_way_client_started()
        assert protocol_factory == udp_protocol_factory_two_way_client_started
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
        full_peername = f"udp_{peer_str}_{sock_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert udp_protocol_factory_two_way_client_started.logger == new_connection.logger
        assert udp_protocol_factory_two_way_client_started.is_owner(new_connection)
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        udp_transport_client.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, udp_protocol_factory_two_way_client_started):
        data = pickle.dumps(udp_protocol_factory_two_way_client_started)
        factory = pickle.loads(data)
        assert factory == udp_protocol_factory_two_way_client_started


class TestServerDatagramProtocolFactoryAllowedSenders:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("ip_address", ['127.0.0.1', '::1'])
    async def test_00_allowed_senders_ok(self, udp_protocol_factory_allowed_senders, udp_transport_server, peer,
                                         connections_manager, queue, echo_encoded, echo_response_encoded, ip_address):
        protocol_factory = udp_protocol_factory_allowed_senders()
        protocol_factory.connection_made(udp_transport_server)
        udp_transport_server.set_protocol(protocol_factory)
        peer = (ip_address, peer[1])
        protocol_factory.datagram_received(echo_encoded, peer)
        await asyncio.wait_for(protocol_factory.wait_num_connected(1), timeout=1)
        udp_transport_server.close()
        await protocol_factory.close()
        assert await queue.get() == (peer, echo_response_encoded)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("ip_address", ['127.0.0.2', '::2'])
    async def test_01_allowed_senders_not_ok(self, udp_protocol_factory_allowed_senders, udp_transport_server, connections_manager,
                                             queue, echo_encoded, echo_response_encoded, ip_address, peer):
        protocol_factory = udp_protocol_factory_allowed_senders()
        protocol_factory.connection_made(udp_transport_server)
        udp_transport_server.set_protocol(protocol_factory)
        peer = (ip_address, peer[1])
        protocol_factory.datagram_received(echo_encoded, peer)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(protocol_factory.wait_num_connected(1), timeout=1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=1)
        udp_transport_server.close()
        await protocol_factory.close()
