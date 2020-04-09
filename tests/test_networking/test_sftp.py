import asyncio
import pytest
import pickle
from pathlib import Path


@pytest.mark.connections('sftp_oneway_all')
class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, connection, sftp_conn, sftp_adaptor, connections_manager,
                                           sftp_factory):
        assert connections_manager.total == 0
        assert connection.logger
        assert connection.conn is None
        connection.connection_made(sftp_conn)
        await connection.wait_connected()
        assert connection.is_connected()
        await asyncio.wait_for(connection.wait_context_set(), timeout=1)
        assert connection._adaptor.context == sftp_adaptor.context
        assert connection._adaptor == sftp_adaptor
        assert sftp_factory.sftp_connection == connection
        assert sftp_conn.get_extra_info('sftp_factory') == sftp_factory
        assert connection.peer == f"sftp_{sftp_adaptor.context['own']}_{sftp_adaptor.context['peer']}"
        assert connection.logger is not None
        assert connection.conn == sftp_conn
        assert connections_manager.total == 1
        assert connections_manager.get(connection.peer) == connection
        sftp_conn.close()
        await connection.wait_closed()
        assert connections_manager.total == 0

    def test_01_is_child(self, connection, parent_name):
        assert connection.is_child(parent_name)
        assert not connection.is_child(f"ABC Server")

    @pytest.mark.asyncio
    async def test_02_pickle(self, connection):
        data = pickle.dumps(connection)
        protocol = pickle.loads(data)
        assert protocol == connection


@pytest.mark.connections('sftp_oneway_server')
class TestConnectionServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, sftp_connection_connected, sftp_factory, fixed_timestamp,
                                    json_rpc_login_request_encoded,json_rpc_logout_request_encoded,
                                    assert_recordings_ok, assert_buffered_file_storage_ok):
        sftp_connection_connected.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1.2)
        sftp_connection_connected.data_received(json_rpc_logout_request_encoded)
        sftp_connection_connected.close()
        await asyncio.wait_for(sftp_connection_connected.wait_closed(), timeout=1)
        await assert_buffered_file_storage_ok
        await assert_recordings_ok


@pytest.mark.connections('sftp_oneway_server')
class TestConnectionServerOSAuth:

    def test_00_password_auth_supported(self, connection):
        assert connection.password_auth_supported()

    @pytest.mark.asyncio
    async def test_01_password_auth_successful(self, connection, sftp_username_password, patch_os_auth_ok,
                                               patch_os_call_args):
        result = await connection.validate_password(*sftp_username_password)
        assert result is True
        patch_os_auth_ok.assert_called_with(*patch_os_call_args)

    @pytest.mark.asyncio
    async def test_02_password_auth_failure(self, connection, sftp_username_password, patch_os_auth_failure,
                                            patch_os_call_args):
        result = await connection.validate_password(*sftp_username_password)
        assert result is False
        patch_os_auth_failure.assert_called_with(*patch_os_call_args)


@pytest.mark.connections('sftp_oneway_client')
class TestConnectionClient:

    @pytest.mark.asyncio
    async def test_00_send(self, sftp_connection_connected, sftp_factory, fixed_timestamp, tmpdir,
                           json_rpc_login_request_encoded):
        sftp_factory.realpath.assert_awaited_with('/')
        await sftp_connection_connected.send(json_rpc_login_request_encoded)
        sftp_factory.put.assert_awaited_with(Path(tmpdir) / "sftp_sent/FILE201901010101000000000000",
                                             remotepath='/')

    @pytest.mark.asyncio
    async def test_01_send_data_adaptor_method(self, sftp_connection_connected, sftp_factory, fixed_timestamp,
                                               json_rpc_login_request_encoded, tmpdir):
        sftp_connection_connected.send_data(json_rpc_login_request_encoded)
        await sftp_connection_connected.wait_tasks_done()
        sftp_factory.put.assert_awaited_with(Path(tmpdir) / "sftp_sent/FILE201901010101000000000000",
                                                  remotepath='/')


@pytest.mark.connections('sftp_oneway_all')
class TestSFTPProtocolFactories:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, protocol_factory_started, connection, sftp_conn,
                                           sftp_factory):
        new_connection = protocol_factory_started()
        assert protocol_factory_started.logger == new_connection.logger
        assert new_connection == connection
        assert protocol_factory_started.is_owner(new_connection)
        new_connection.connection_made(sftp_conn)
        sftp_conn._owner = new_connection
        await asyncio.wait_for(protocol_factory_started.wait_num_connected(1), timeout=1)
        await asyncio.wait_for(new_connection.wait_connected(), timeout=1)
        sftp_conn.close()
        await asyncio.wait_for(protocol_factory_started.close(), timeout=2)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, protocol_factory):
        data = pickle.dumps(protocol_factory)
        factory = pickle.loads(data)
        assert factory == protocol_factory
        await protocol_factory.close()
