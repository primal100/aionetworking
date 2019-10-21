import asyncio
import pickle
import pytest
import asyncssh

from lib.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestClientStartStop:
    @pytest.mark.asyncio
    async def test_00_client_start(self, sftp_server_started, sftp_client, extra_server_inet_sftp):
        assert not sftp_client.is_started()
        async with sftp_client as conn:
            assert sftp_client.is_started()
            assert conn.conn
            assert sftp_client.conn
            assert sftp_client.sftp
            assert sftp_client.sftp_conn
            await asyncio.wait_for(conn.wait_context_set(), timeout=1)
            assert conn.context == extra_server_inet_sftp
        assert sftp_client.is_closing()

    @pytest.mark.asyncio
    async def test_01_client_close(self, sftp_server_started, sftp_client):
        await sftp_client.connect()
        await sftp_client.close()
        assert sftp_client.is_closing()

    @pytest.mark.asyncio
    async def test_02_client_pickle(self, sftp_client):
        data = pickle.dumps(sftp_client)
        new_client = pickle.loads(data)
        assert new_client == sftp_client

    @pytest.mark.asyncio
    async def test_03_client_wrong_password(self, sftp_server_started, sftp_client_wrong_password):
        assert not sftp_client_wrong_password.is_started()
        with pytest.raises(asyncssh.misc.PermissionDenied):
            await sftp_client_wrong_password.connect()
