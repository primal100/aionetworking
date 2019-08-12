import asyncio
import pytest

from lib.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestClientStartStop:
    @pytest.mark.asyncio
    async def test_00_client_start(self, client_sender):
        assert not client_sender.is_started()
        conn = await client_sender.connect()
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
