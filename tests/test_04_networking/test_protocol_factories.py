import asyncio
import datetime
import pytest
import pickle
from aionetworking.compatibility import create_task


@pytest.mark.connections()
class TestProtocolFactoriesShared:

    @pytest.mark.asyncio
    async def test_00_pickle_protocol_factory(self, protocol_factory):
        data = pickle.dumps(protocol_factory)
        factory = pickle.loads(data)
        assert factory == protocol_factory
        await protocol_factory.close()


class TestStreamProtocolFactories:

    @pytest.mark.connections('tcp_all_all')
    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory_started, connection, transport):
        new_connection = protocol_factory_started()
        assert protocol_factory_started.logger == new_connection.logger
        assert new_connection == connection
        assert protocol_factory_started.is_owner(new_connection)
        new_connection.connection_made(transport)
        new_connection.transport.set_protocol(new_connection)
        await asyncio.wait_for(protocol_factory_started.wait_num_connected(1), timeout=1)
        await asyncio.wait_for(new_connection.wait_connected(), timeout=1)
        new_connection.transport.close()
        await asyncio.wait_for(protocol_factory_started.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)

    @pytest.mark.connections('tcp_oneway_all')
    @pytest.mark.asyncio
    async def test_01_protocol_factory_custom_codec_config(self, protocol_factory_codec_kwargs,
                                                           json_codec_with_kwargs, transport,
                                                           json_rpc_login_request_encoded):
        new_connection = protocol_factory_codec_kwargs()
        assert new_connection.codec_config == {'test_param': 'abc'}
        new_connection.connection_made(transport)
        transport.set_protocol(new_connection)
        new_connection.data_received(json_rpc_login_request_encoded)
        adaptor = new_connection._adaptor
        assert adaptor.codec_config == {'test_param': 'abc'}
        assert adaptor.codec.msg_obj == json_codec_with_kwargs.msg_obj
        assert adaptor.codec.test_param == json_codec_with_kwargs.test_param

    @pytest.mark.connections('tcp_all_all')
    @pytest.mark.asyncio
    async def test_02_protocol_factory_connections_expire(self, protocol_factory_expire_connections,
                                                          transport, echo_encoded, echo_response):
        new_connection = protocol_factory_expire_connections()
        new_connection.connection_made(transport)
        transport.set_protocol(new_connection)
        connection_time = new_connection.last_msg
        assert isinstance(connection_time, datetime.datetime)
        await asyncio.sleep(0.1)
        new_connection.data_received(echo_encoded)
        data_received_time = new_connection.last_msg
        assert data_received_time > connection_time
        assert not new_connection.is_closing()
        await asyncio.sleep(0.5)
        assert not new_connection.is_closing()
        new_connection.send_data(echo_response)
        assert new_connection.last_msg > data_received_time
        await asyncio.sleep(0.5)
        assert not new_connection.is_closing()
        await asyncio.sleep(0.8)
        assert new_connection.is_closing()
        await protocol_factory_expire_connections.wait_all_closed()


@pytest.mark.connections('udp_oneway_server')
class TestOneWayServerDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory_started, connection, json_rpc_logout_request_encoded,
                                           transport, client_sock, server_sock, json_rpc_login_request_encoded,
                                           connections_manager, assert_buffered_file_storage_ok, json_objects,
                                           client_sock_str, server_sock_str):
        protocol_factory = protocol_factory_started()
        assert protocol_factory == protocol_factory_started
        protocol_factory.connection_made(transport)
        transport.set_protocol(protocol_factory)
        protocol_factory.datagram_received(json_rpc_login_request_encoded, client_sock)
        assert connections_manager.total == 1
        await asyncio.wait_for(protocol_factory.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{server_sock_str}_{client_sock_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert protocol_factory.logger == new_connection.logger
        assert protocol_factory.is_owner(new_connection)
        protocol_factory.datagram_received(json_rpc_logout_request_encoded, client_sock)
        assert connections_manager.total == 1
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        transport.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0
        await assert_buffered_file_storage_ok

    @pytest.mark.asyncio
    async def test_01_protocol_factory_connections_expire(self, protocol_factory_expire_connections,
                                                          transport, echo_encoded, echo_response, client_sock,
                                                          connections_manager, server_sock_str, client_sock_str):
        protocol_factory = protocol_factory_expire_connections()
        protocol_factory.connection_made(transport)
        transport.set_protocol(protocol_factory)
        protocol_factory.datagram_received(echo_encoded, client_sock)
        await asyncio.wait_for(protocol_factory_expire_connections.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{server_sock_str}_{client_sock_str}"
        new_connection = connections_manager.get(full_peername)
        msg_received_time = new_connection.last_msg
        assert isinstance(msg_received_time, datetime.datetime)
        assert not new_connection.is_closing()
        await asyncio.sleep(0.5)
        assert not new_connection.is_closing()
        new_connection.send_data(echo_response)
        assert new_connection.last_msg > msg_received_time
        await asyncio.sleep(0.5)
        assert not new_connection.is_closing()
        await asyncio.sleep(0.8)
        assert new_connection.is_closing()
        await protocol_factory_expire_connections.wait_all_closed()


@pytest.mark.connections('udp_oneway_client')
class TestOneWayClientDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory_started, connection, json_rpc_login_request_encoded,
                                           transport, client_sock, client_sock_str, server_sock_str, server_sock,
                                           connections_manager, queue):
        protocol_factory = protocol_factory_started()
        assert protocol_factory == protocol_factory_started
        protocol_factory.connection_made(transport)
        transport.set_protocol(protocol_factory)
        conn = protocol_factory.new_peer()
        assert connections_manager.total == 1
        full_peername = f"udp_{client_sock_str}_{server_sock_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        conn.send(json_rpc_login_request_encoded)
        msg = await queue.get()
        assert msg == (server_sock, json_rpc_login_request_encoded)
        assert protocol_factory.logger == new_connection.logger
        assert protocol_factory.is_owner(new_connection)
        transport.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0


@pytest.mark.connections('udp_twoway_server')
class TestTwoWayServerDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory_started, connection, server_sock, client_sock_str,
                                           server_sock_str, echo_encoded, transport, echo_response_encoded,
                                           client_sock, connections_manager, queue):
        protocol_factory = protocol_factory_started()
        assert protocol_factory == protocol_factory_started
        protocol_factory.connection_made(transport)
        transport.set_protocol(protocol_factory)
        protocol_factory.datagram_received(echo_encoded, client_sock)
        assert connections_manager.total == 1
        await asyncio.wait_for(protocol_factory.wait_num_connected(1), timeout=1)
        full_peername = f"udp_{server_sock_str}_{client_sock_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert protocol_factory.logger == new_connection.logger
        assert protocol_factory.is_owner(new_connection)
        msg = await queue.get()
        assert msg == (client_sock, echo_response_encoded)
        protocol_factory.datagram_received(echo_encoded, client_sock)
        msg = await queue.get()
        assert msg == (client_sock, echo_response_encoded)
        assert connections_manager.total == 1
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        transport.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0


@pytest.mark.connections('udp_twoway_client')
class TestTwoWayClientDatagramProtocolFactory:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory_started, connection, echo_response_encoded, transport,
                                           echo_encoded, server_sock, client_sock, connections_manager, queue,
                                           echo_response_object, client_sock_str, server_sock_str):
        protocol_factory = protocol_factory_started()
        assert protocol_factory == protocol_factory_started
        protocol_factory.connection_made(transport)
        transport.set_protocol(protocol_factory)
        conn = protocol_factory.new_peer()
        assert connections_manager.total == 1
        task = create_task(conn.echo())
        msg = await queue.get()
        assert msg == (server_sock, echo_encoded)
        protocol_factory.datagram_received(echo_response_encoded, server_sock)
        response = await asyncio.wait_for(task, timeout=1)
        assert response == echo_response_object
        assert connections_manager.total == 1
        full_peername = f"udp_{client_sock_str}_{server_sock_str}"
        new_connection = connections_manager.get(full_peername)
        assert new_connection.is_connected()
        assert protocol_factory_started.logger == new_connection.logger
        assert protocol_factory_started.is_owner(new_connection)
        assert id(connections_manager.get(full_peername)) == id(new_connection)
        transport.close()
        await asyncio.wait_for(protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)
        assert connections_manager.total == 0

