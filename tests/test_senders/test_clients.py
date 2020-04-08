import asyncio
import pickle
import pytest
import asyncssh

from aionetworking.networking.exceptions import RemoteConnectionClosedError

###Required for skipif in fixture params###
from aionetworking.compatibility import datagram_supported, is_proactor, supports_pipe_or_unix_connections


class TestClientStartStop:
    @pytest.mark.asyncio
    async def test_00_client_start(self, client):
        assert not client.is_started()
        async with client as conn:
            assert client.is_started()
            assert conn.transport
            assert client.transport
            assert client.conn
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_01_check_client_context(self, client_connected, client_context):
        assert client_connected.conn.context == client_context

    @pytest.mark.asyncio
    async def test_02_check_server_context(self, client_connected, server_context, connections_manager):
        peername = f"{client_connected.conn.peer_prefix}_{server_context['own']}_{server_context['peer']}"
        server_connection = connections_manager.get(peername)
        assert server_connection.context == server_context

    @pytest.mark.asyncio
    async def test_03_client_connect_close(self, server_started, client):
        await client.connect()
        await client.close()
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_04_client_pickle(self, client):
        data = pickle.dumps(client)
        new_client = pickle.loads(data)
        assert new_client == client


@pytest.mark.connections('sslsftp_oneway_all')
class TestSSLAndSFTPClient:
    @pytest.mark.asyncio
    async def test_00_client_start(self, client):
        assert not client.is_started()
        async with client as conn:
            assert client.is_started()
            assert client.conn
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_01_check_client_context(self, client_connected, client_context):
        assert client_connected.conn.context == client_context

    @pytest.mark.asyncio
    async def test_02_check_server_context(self, client_connected, server_context, connections_manager):
        peername = f"{client_connected.conn.peer_prefix}_{server_context['own']}_{server_context['peer']}"
        server_connection = connections_manager.get(peername)
        assert server_connection.context == server_context

    @pytest.mark.asyncio
    async def test_03_client_connect_close(self, server_started, client):
        await client.connect()
        await client.close()
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_04_client_pickle(self, client):
        data = pickle.dumps(client)
        new_client = pickle.loads(data)
        assert new_client == client


@pytest.mark.connections('sftp_oneway_all')
class TestSFTPClient:
    @pytest.mark.asyncio
    async def test_00_client_wrong_password(self, server_started, sftp_client_wrong_password):
        with pytest.raises(asyncssh.misc.PermissionDenied):
            await sftp_client_wrong_password.connect()


@pytest.mark.connections('inet_twoway_all')
class TestClientAllowedSenders:
    @pytest.mark.asyncio
    async def test_00_client_connect_allowed(self, server_allowed_senders, client_allowed_senders, echo_encoded,
                                             echo_response_object):
        async with client_allowed_senders as conn:
            response = await asyncio.wait_for(conn.send_data_and_wait(1, echo_encoded), timeout=1)
            assert response == echo_response_object

    @pytest.mark.asyncio
    async def test_01_client_connect_not_allowed(self, server_allowed_senders, client_incorrect_sender,
                                                 echo_encoded):
        async with client_incorrect_sender as conn:
            with pytest.raises((ConnectionResetError, ConnectionAbortedError, RemoteConnectionClosedError, asyncio.TimeoutError)):
                await asyncio.wait_for(conn.send_data_and_wait(1, echo_encoded), 2)


@pytest.mark.skip
class TestConnectionsExpire:
    @pytest.mark.asyncio
    async def test_00_connections_expire(self, server_expire_connections, client_expire_connections):
        async with client_expire_connections as conn:
            await asyncio.sleep(0.2)
            assert not conn.transport.is_closing()
            await asyncio.sleep(1.2)
            assert conn.transport.is_closing()

    @pytest.mark.asyncio
    async def test_01_connections_expire_after_msg_received(self, server_expire_connections,
                                                            client_expire_connections, echo_encoded):
        async with client_expire_connections as conn:
            await asyncio.sleep(0.5)
            conn.simple()
            await asyncio.sleep(0.8)
            assert not conn.transport.is_closing()
            await asyncio.sleep(0.4)
            assert conn.transport.is_closing()

    @pytest.mark.asyncio
    async def test_02_connections_expire_after_msg_sent(self, server_expire_connections,
                                                        client_expire_connections):
        async with client_expire_connections as conn:
            await asyncio.sleep(0.5)
            await conn.echo()
            await asyncio.sleep(0.8)
            assert not conn.transport.is_closing()
            await asyncio.sleep(0.4)
            assert conn.transport.is_closing()
