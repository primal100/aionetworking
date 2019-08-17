import pickle
import pytest
import asyncio

from lib.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestClientStartStop:
    @pytest.mark.asyncio
    async def test_00_client_start(self, client_sender, server_receiver, context_pipe_client, expected_server_context, expected_client_context):
        assert not client_sender.is_started()
        conn = await asyncio.wait_for(client_sender.connect(), timeout=1)
        assert client_sender.is_started()
        assert conn.transport
        assert client_sender.transport
        assert client_sender.conn

    @pytest.mark.asyncio
    async def test_01_client_stop(self, client_connected):
        client, connection = client_connected
        await client.close()
        assert client.is_closing()

    @pytest.mark.asyncio
    async def test_02_client_context_manager(self, client_sender):
        assert not client_sender.is_started()
        async with client_sender as conn:
            assert client_sender.is_started()
            assert conn.transport
            assert client_sender.transport
            assert client_sender.conn
        assert client_sender.is_closing()

    @pytest.mark.asyncio
    async def test_03_client_pickle(self, client_sender):
        data = pickle.dumps(client_sender)
        client = pickle.loads(data)
        assert client == client_sender
