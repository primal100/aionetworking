import pickle
import pytest
import asyncio

from lib.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
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
