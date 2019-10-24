import asyncio
import pickle
import pytest

from lib.networking.exceptions import RemoteConnectionClosedError

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported, is_proactor
from lib.utils import supports_pipe_or_unix_connections


class TestClientStartStop:
    @pytest.mark.asyncio
    async def test_00_client_start(self, server_started, client, server_context, client_context, connections_manager):
        assert not client.is_started()
        async with client as conn:
            assert client.is_started()
            assert conn.transport
            assert sorted(conn.context.keys()) == sorted(client_context.keys())
            assert client.transport
            assert client.conn
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_01_client_connect_close(self, server_started, client):
        await client.connect()
        await client.close()
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_02_tcp_client_cannot_connect(self, tcp_client_one_way):
        with pytest.raises(ConnectionRefusedError):
            await tcp_client_one_way.connect()

    @pytest.mark.asyncio
    async def test_03_client_pickle(self, client):
        data = pickle.dumps(client)
        new_client = pickle.loads(data)
        assert new_client == client


class TestClientAllowedSenders:
    @pytest.mark.asyncio
    async def test_00_tcp_client_connect_allowed(self, tcp_server_started_allowed_senders, tcp_client_allowed_senders,
                                                echo_encoded, echo_response_object):
        async with tcp_client_allowed_senders as conn:
            response = await asyncio.wait_for(conn.send_data_and_wait(1, echo_encoded), timeout=1)
            assert response == echo_response_object

    @pytest.mark.asyncio
    async def test_01_tcp_client_connect_not_allowed_ip4(self, tcp_server_started_wrong_senders,
                                                         tcp_client_wrong_senders, echo_encoded):
        async with tcp_client_wrong_senders as conn:
            with pytest.raises((ConnectionResetError, ConnectionAbortedError, RemoteConnectionClosedError)):
                await conn.send_data_and_wait(1, echo_encoded)

    @pytest.mark.asyncio
    async def test_02_udp_client_connect_allowed(self, udp_server_started_allowed_senders, udp_client_allowed_senders,
                                                 echo_encoded, echo_response_object):
        async with udp_client_allowed_senders as conn:
            response = await asyncio.wait_for(conn.send_data_and_wait(1, echo_encoded), timeout=1)
            assert response == echo_response_object

    @pytest.mark.asyncio
    async def test_03_udp_client_connect_not_allowed(self, udp_server_started_wrong_senders, udp_client_wrong_senders,
                                                     echo_encoded):
        async with udp_client_wrong_senders as conn:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(conn.send_data_and_wait(1, echo_encoded), timeout=1)
