import asyncio
import pytest
import pickle
import signal
import os
from unittest.mock import call

from aionetworking.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from aionetworking.compatibility import datagram_supported, supports_pipe_or_unix_connections


ready_call = call('READY=1')
stopping_call = call('STOPPING=1')
reloading_call = call('RELOADING=1')


def status_call(msg):
    return call(f'STATUS={msg}')


class TestServerStartStop:
    @pytest.mark.asyncio
    async def test_00_server_start(self, server_receiver, capsys):
        assert not server_receiver.is_started()
        task = asyncio.create_task(server_receiver.start())
        await asyncio.wait_for(server_receiver.wait_started(), timeout=2)
        assert server_receiver.is_started()
        captured = capsys.readouterr()
        assert captured.out.startswith("Serving")
        await asyncio.wait_for(task, timeout=2)

    @pytest.mark.asyncio
    async def test_01_serve_forever(self, server_receiver, capsys):
        assert not server_receiver.is_started()
        task = asyncio.create_task(server_receiver.serve_forever())
        await asyncio.wait_for(server_receiver.wait_started(), timeout=2)
        assert server_receiver.is_started()
        captured = capsys.readouterr()
        assert captured.out.startswith("Serving")
        await asyncio.sleep(2)
        assert not task.done()
        assert server_receiver.is_started()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert server_receiver.is_closed()

    @pytest.mark.asyncio
    async def test_02_server_close(self, server_started):
        assert server_started.is_started()
        task = asyncio.create_task(server_started.close())
        await asyncio.wait_for(server_started.wait_stopped(), timeout=2)
        assert not server_started.is_started()
        await asyncio.wait_for(task, timeout=2)

    @pytest.mark.asyncio
    async def test_03_server_wait_started(self, server_receiver, capsys):
        assert not server_receiver.is_started()
        task = asyncio.create_task(server_receiver.wait_started())
        await asyncio.sleep(0)
        assert not task.done()
        await server_receiver.start()
        assert server_receiver.is_started()
        await asyncio.wait_for(task, timeout=2)
        captured = capsys.readouterr()
        assert captured.out.startswith("Serving")

    @pytest.mark.asyncio
    async def test_04_server_stop_wait(self, server_started):
        assert server_started.is_started()
        task = asyncio.create_task(server_started.wait_stopped())
        await asyncio.sleep(0)
        assert not task.done()
        await server_started.close()
        assert server_started.is_closing()
        await asyncio.wait_for(task, timeout=2)

    @pytest.mark.asyncio
    async def test_05_server_already_started(self, server_started):
        assert server_started.is_started()
        with pytest.raises(ServerException):
            await server_started.start()

    @pytest.mark.asyncio
    async def test_06_server_never_started(self, server_receiver):
        assert server_receiver.is_closing()
        with pytest.raises(ServerException):
            await server_receiver.close()

    @pytest.mark.asyncio
    async def test_07_server_already_stopped(self, server_started):
        assert server_started.is_started()
        await server_started.close()
        assert not server_started.is_started()
        with pytest.raises(ServerException):
            await server_started.close()

    @pytest.mark.asyncio
    async def test_08_server_start_quiet(self, server_quiet, capsys):
        assert not server_quiet.is_started()
        task = asyncio.create_task(server_quiet.start())
        await asyncio.wait_for(server_quiet.wait_started(), timeout=2)
        assert server_quiet.is_started()
        captured = capsys.readouterr()
        assert captured.out == ''
        await asyncio.wait_for(task, timeout=2)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('signal_num', [
        pytest.param(signal.SIGINT, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only')),
        pytest.param(signal.SIGTERM, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
    ])
    async def test_09_serve_until_close_signal(self, server_quiet, signal_num, patch_systemd, server_port):
        assert not server_quiet.is_started()
        task = asyncio.create_task(server_quiet.serve_until_close_signal())
        await asyncio.wait_for(server_quiet.wait_started(), timeout=2)
        status = next(server_quiet.listening_on_msgs)
        os.kill(os.getpid(), signal_num)
        await asyncio.wait_for(task, timeout=2)
        assert server_quiet.is_closed()
        if patch_systemd:
            daemon, journal = patch_systemd
            daemon.notify.assert_has_calls([status_call(status), ready_call, stopping_call])
            assert daemon.notify.call_count == 3

    @pytest.mark.asyncio
    async def test_10_pickle_server(self, server_receiver):
        data = pickle.dumps(server_receiver)
        server = pickle.loads(data)
        assert server == server_receiver
