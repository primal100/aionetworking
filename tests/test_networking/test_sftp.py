import asyncio
import pytest
import pickle
from pathlib import Path

from aionetworking.formats import get_recording_from_file
from aionetworking.utils import alist


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, sftp_protocol, sftp_conn, sftp_adaptor, connections_manager,
                                           sftp_factory):
        assert connections_manager.total == 0
        assert sftp_protocol.logger
        assert sftp_protocol.conn is None
        sftp_protocol.connection_made(sftp_conn)
        await sftp_protocol.wait_connected()
        assert sftp_protocol.is_connected()
        await asyncio.wait_for(sftp_protocol.wait_context_set(), timeout=1)
        assert sftp_protocol._adaptor.context == sftp_adaptor.context
        assert sftp_protocol._adaptor == sftp_adaptor
        assert sftp_factory.sftp_connection == sftp_protocol
        assert sftp_conn.get_extra_info('sftp_factory') == sftp_factory
        assert sftp_protocol.peer == f"sftp_{sftp_adaptor.context['own']}_{sftp_adaptor.context['peer']}"
        assert sftp_protocol.logger is not None
        assert sftp_protocol.conn == sftp_conn
        assert connections_manager.total == 1
        assert connections_manager.get(sftp_protocol.peer) == sftp_protocol
        sftp_conn.close()
        await sftp_protocol.wait_closed()
        assert connections_manager.total == 0


class TestConnectionServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, sftp_protocol_one_way_server, json_rpc_login_request_encoded,
                                    sftp_factory_server, json_rpc_logout_request_encoded, json_recording_data, json_codec,
                                    json_objects, sftp_one_way_conn_server):
        sftp_protocol_one_way_server.connection_made(sftp_one_way_conn_server)
        sftp_protocol_one_way_server.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1.2)
        sftp_protocol_one_way_server.data_received(json_rpc_logout_request_encoded)
        sftp_one_way_conn_server.close()
        await asyncio.wait_for(sftp_protocol_one_way_server.wait_closed(), timeout=1)
        expected_file = Path(tmp_path/'data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects
        expected_file = Path(tmp_path / 'recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist((get_recording_from_file(expected_file)))
        assert (packets[1].timestamp - packets[0].timestamp).total_seconds() > 1
        packets[0] = packets[0]._replace(timestamp=json_recording_data[0].timestamp)
        packets[1] = packets[1]._replace(timestamp=json_recording_data[1].timestamp)
        assert packets == json_recording_data

    def test_01_is_child(self, sftp_protocol_one_way_server, sock_str):
        assert sftp_protocol_one_way_server.is_child(f"SFTP Server {sock_str}")
        assert not sftp_protocol_one_way_server.is_child(f"ABC Server {sock_str}")

    @pytest.mark.asyncio
    async def test_02_pickle(self, sftp_protocol_one_way_server):
        data = pickle.dumps(sftp_protocol_one_way_server)
        protocol = pickle.loads(data)
        assert protocol == sftp_protocol_one_way_server

    @pytest.mark.asyncio
    async def test_03_close(self, sftp_protocol_one_way_server, sftp_one_way_conn_server,
                            sftp_factory_server, json_rpc_login_request_encoded, json_rpc_login_request_object,
                            tmp_path, json_codec, json_recording_data):
        sftp_protocol_one_way_server.connection_made(sftp_one_way_conn_server)
        file_path = Path(tmp_path) / "test"
        f = file_path.open(mode='wb')
        f.write(json_rpc_login_request_encoded)
        sftp_factory_server.close(f)
        await sftp_factory_server.wait_closed()
        assert not file_path.exists()
        sftp_one_way_conn_server.close()
        await asyncio.wait_for(sftp_protocol_one_way_server.wait_closed(), timeout=1)
        expected_file = Path(tmp_path / 'data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == [json_rpc_login_request_object]
        expected_file = Path(tmp_path / 'recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist((get_recording_from_file(expected_file)))
        packets[0] = packets[0]._replace(timestamp=json_recording_data[0].timestamp)
        assert packets[0] == json_recording_data[0]


class TestConnectionServerOSAuth:

    def test_00_password_auth_supported(self, sftp_protocol_one_way_server):
        assert sftp_protocol_one_way_server.password_auth_supported()

    @pytest.mark.asyncio
    async def test_01_password_auth_successful(self, sftp_protocol_one_way_server, sftp_username_password,
                                               patch_os_auth_ok, patch_os_call_args):
        result = await sftp_protocol_one_way_server.validate_password(*sftp_username_password)
        assert result is True
        patch_os_auth_ok.assert_called_with(*patch_os_call_args)

    @pytest.mark.asyncio
    async def test_02_password_auth_failure(self, sftp_protocol_one_way_server, sftp_username_password,
                                            patch_os_auth_failure, patch_os_call_args):
        result = await sftp_protocol_one_way_server.validate_password(*sftp_username_password)
        assert result is False
        patch_os_auth_failure.assert_called_with(*patch_os_call_args)


class TestConnectionClient:

    @pytest.mark.asyncio
    async def test_00_send(self, sftp_protocol_one_way_client, sftp_factory_client,
                           sftp_one_way_conn_client, json_rpc_login_request_encoded, patch_datetime_now, tmpdir):
        sftp_protocol_one_way_client.connection_made(sftp_one_way_conn_client)
        await sftp_protocol_one_way_client.set_sftp(sftp_factory_client)
        sftp_factory_client.realpath.assert_awaited_with('/')
        task = sftp_protocol_one_way_client.send(json_rpc_login_request_encoded)
        await task
        sftp_factory_client.put.assert_awaited_with(Path(tmpdir) / "sftp_sent/FILE20190101010101000000",
                                                    remotepath='/')

    @pytest.mark.asyncio
    async def test_01_send_data_adaptor_method(self, sftp_protocol_one_way_client, json_rpc_login_request_encoded,
                                               sftp_factory_client, sftp_one_way_conn_client, patch_datetime_now,
                                               tmpdir):
        sftp_protocol_one_way_client.connection_made(sftp_one_way_conn_client)
        await sftp_protocol_one_way_client.set_sftp(sftp_factory_client)
        sftp_factory_client.realpath.assert_awaited_with('/')
        sftp_protocol_one_way_client.send_data(json_rpc_login_request_encoded)
        await sftp_protocol_one_way_client.wait_tasks_done()
        sftp_factory_client.put.assert_awaited_with(Path(tmpdir) / "sftp_sent/FILE20190101010101000000",
                                                    remotepath='/')

    def test_02_is_child(self, one_way_client_connection, sftp_protocol_one_way_client):
        assert sftp_protocol_one_way_client.is_child("SFTP Client 127.0.0.1:0")
        assert not sftp_protocol_one_way_client.is_child("ABC Client 127.0.0.1:0")

    @pytest.mark.asyncio
    async def test_03_pickle(self, one_way_client_connection):
        data = pickle.dumps(one_way_client_connection)
        protocol = pickle.loads(data)
        assert protocol == one_way_client_connection


class TestSFTPProtocolFactories:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, sftp_protocol_factory, sftp_protocol, sftp_conn,
                                           sftp_factory):
        new_connection = sftp_protocol_factory()
        assert sftp_protocol_factory.logger == new_connection.logger
        assert new_connection == sftp_protocol
        assert sftp_protocol_factory.is_owner(new_connection)
        new_connection.connection_made(sftp_conn)
        sftp_conn._owner = new_connection
        await asyncio.wait_for(sftp_protocol_factory.wait_num_connected(1), timeout=1)
        await asyncio.wait_for(new_connection.wait_connected(), timeout=1)
        sftp_conn.close()
        await asyncio.wait_for(sftp_protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)

    @pytest.mark.asyncio
    async def test_01_protocol_factory_connections_expire(self, sftp_protocol_factory_server_expired_connections_started,
                                                          server_sftp_conn, json_rpc_login_request_encoded):
        new_connection = sftp_protocol_factory_server_expired_connections_started()
        new_connection.connection_made(server_sftp_conn)
        server_sftp_conn._owner = new_connection
        connection_time = new_connection.last_msg
        await asyncio.sleep(0.02)
        new_connection.data_received(json_rpc_login_request_encoded)
        assert new_connection.last_msg > connection_time
        assert not new_connection.is_closing()
        await asyncio.sleep(0.3)
        assert not new_connection.is_closing()
        await asyncio.sleep(1)
        assert new_connection.is_closing()
        await sftp_protocol_factory_server_expired_connections_started.wait_all_closed()

    @pytest.mark.asyncio
    async def test_02_pickle_protocol_factory(self, sftp_protocol_factory):
        data = pickle.dumps(sftp_protocol_factory)
        factory = pickle.loads(data)
        assert factory == sftp_protocol_factory
        await sftp_protocol_factory.close()
