import asyncio
import pytest
import pickle

from lib.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestServerStartStop:
    @pytest.mark.asyncio
    async def test_00_server_start(self, server_receiver, capsys):
        assert not server_receiver.is_started()
        task = asyncio.create_task(server_receiver.start())
        try:
            await asyncio.wait_for(server_receiver.wait_started(), timeout=1)
            assert server_receiver.is_started()
            captured = capsys.readouterr()
            assert captured.out.startswith("Serving")
        except asyncio.TimeoutError:
            pass
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_01_server_close(self, server_started):
        assert server_started.is_started()
        task = asyncio.create_task(server_started.stop())
        try:
            await asyncio.wait_for(server_started.wait_stopped(), timeout=1)
            assert not server_started.is_started()
        except asyncio.TimeoutError:
            pass
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_02_server_start_wait(self, server_receiver, capsys):
        assert not server_receiver.is_started()
        try:
            await asyncio.wait_for(server_receiver.start_wait(), timeout=1)
            assert server_receiver.is_started()
            captured = capsys.readouterr()
            assert captured.out.startswith("Serving")
        except asyncio.TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_03_server_stop_wait(self, server_started):
        assert server_started.is_started()
        try:
            await asyncio.wait_for(server_started.stop_wait(), timeout=1)
            assert not server_started.is_started()
        except asyncio.TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_04_server_already_started(self, server_started):
        assert server_started.is_started()
        with pytest.raises(ServerException):
            await server_started.start_wait()

    @pytest.mark.asyncio
    async def test_05_server_never_started(self, server_receiver):
        assert not server_receiver.is_started()
        with pytest.raises(ServerException):
            await server_receiver.stop_wait()

    @pytest.mark.asyncio
    async def test_06_server_already_stopped(self, server_started):
        assert server_started.is_started()
        await server_started.stop_wait()
        assert not server_started.is_started()
        with pytest.raises(ServerException):
            await server_started.stop_wait()

    @pytest.mark.asyncio
    async def test_07_server_start_quiet(self, server_receiver_quiet, capsys):
        assert not server_receiver_quiet.is_started()
        task = asyncio.create_task(server_receiver_quiet.start())
        try:
            await asyncio.wait_for(server_receiver_quiet.wait_started(), timeout=1)
            assert server_receiver_quiet.is_started()
            captured = capsys.readouterr()
            assert captured.out == ''
        except asyncio.TimeoutError:
            pass
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_08_pickle_server(self, server_receiver):
        data = pickle.dumps(server_receiver)
        server = pickle.loads(data)
        assert server == server_receiver
