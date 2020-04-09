from aionetworking.runners import run_server_default_tags
import asyncio
import pytest
import signal
import os
from aionetworking.compatibility import supports_keyboard_interrupt, py38
from aionetworking.utils import wait_server_started_raise_signal, assert_reload_ok
from threading import Thread, Event


class TestRunnerDirect:
    @pytest.mark.skipifwindowsxdist
    @pytest.mark.parametrize('signal_num', [
        pytest.param(signal.SIGINT, marks=pytest.mark.skipif(not supports_keyboard_interrupt(),
                                                             reason='Loop does not support keyboard interrupts')),
        pytest.param(signal.SIGTERM, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
    ])
    def test_00_run_server(self, tmp_config_file, all_paths, signal_num, server_sock, new_event_loop, capsys,
                           load_all_yaml_tags, executor):
        ip = server_sock[0]
        fut = executor.submit(wait_server_started_raise_signal, signal_num, ip, capsys)
        try:
            run_server_default_tags(tmp_config_file, paths=all_paths, timeout=3)
        except asyncio.TimeoutError:
            pass
        out, port = fut.result(timeout=2)
        out += capsys.readouterr().out
        assert out == f'Serving TCP Server on {ip}:{port}\n'

    @pytest.mark.parametrize('signal_num', [
        pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
    ])
    def test_02_runner_reload(self, tmp_config_file, all_paths, server_sock, signal_num, capsys, executor,
                              new_event_loop):
        new_host = '127.0.0.2'
        fut = executor.submit(assert_reload_ok, signal_num, server_sock[0], new_host, tmp_config_file, capsys)
        try:
            run_server_default_tags(tmp_config_file, paths=all_paths, timeout=6)
        except asyncio.TimeoutError:
            pass
        out, port = fut.result(1)
        out += capsys.readouterr().out
        assert out == f'Serving TCP Server on {new_host}:{port}\n'
