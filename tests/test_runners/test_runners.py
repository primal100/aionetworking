from aionetworking.runners import run_server_default_tags
import asyncio
import pytest
import signal
import os
import time
import sys
from aionetworking.utils import is_listening_on, wait_on_capsys, port_from_out, assert_reload_ok


class TestRunnerDirect:
    def test_00_run_server(self, tmp_config_file, all_paths, server_sock, capsys):
        host = server_sock[0]
        run_server_default_tags(tmp_config_file, paths=all_paths, duration=3)
        out, port = wait_on_capsys(capsys)
        assert out == f'Serving TCP Server on {host}:{port}\n'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('signal_num', [
        pytest.param(getattr(signal, 'CTRL_C_EVENT', None), marks=pytest.mark.skip(reason="Doesn't work")),
        pytest.param(signal.SIGINT, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX Only')),
        pytest.param(signal.SIGTERM, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
    ])
    async def test_01_run_server_until_stopped(self, tmp_config_file, all_paths, signal_num, server_sock, new_event_loop,
                                               capsys, load_all_yaml_tags, sample_server_script):
        host = server_sock[0]

        async def step(p, host):
            s = await p.stdout.readline()
            s = s.decode()
            if not s:
                print(await p.stderr.read())
                raise AssertionError
            else:
                port = port_from_out(s)
                assert s == f'Serving TCP Server on {host}:{port}\r\n'
                assert is_listening_on((host, port), pid=p.pid)
                # ensure that child process gets to run_forever
                time.sleep(0.5)
                os.kill(p.pid, signal_num)

        p = await asyncio.create_subprocess_exec(sys.executable, sample_server_script, str(tmp_config_file),
                                                 env=dict(os.environ), stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE)
        try:
            await step(p, host)
            exit_code = await asyncio.wait_for(p.wait(), 5)
            assert exit_code == 0
        except Exception as e:
            p.kill()
            raise

    @pytest.mark.parametrize('signal_num', [
        pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='Not applicable for Windows'))
    ])
    def test_02_runner_reload(self, tmp_config_file, all_paths, server_sock, signal_num, capsys, executor,
                              new_event_loop):
        new_host = '::1'
        fut = executor.submit(assert_reload_ok, signal_num, server_sock[0], new_host, tmp_config_file, capsys)
        run_server_default_tags(tmp_config_file, paths=all_paths, duration=10)
        out, port = fut.result(1)
        out += capsys.readouterr().out
        assert out == f'Serving TCP Server on {new_host}:{port}\n'
