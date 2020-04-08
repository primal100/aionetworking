from aionetworking.runners import run_server_default_tags
import pytest
import signal
import time
import os
from aionetworking.compatibility import supports_keyboard_interrupt, py38
from aionetworking.utils import wait_listening_on_sync, is_listening_on
from threading import Thread, Event


def raise_signal(signal_num, host, port):
    time.sleep(1)
    wait_listening_on_sync((host, port))
    if py38:
        signal.raise_signal(signal_num)
    else:
        os.kill(os.getpid(), signal_num)


@pytest.mark.skip
@pytest.mark.parametrize('signal_num', [
    pytest.param(signal.SIGINT, marks=pytest.mark.skipif(not supports_keyboard_interrupt(), reason='Loop does not support keyboard interrupts')),
    pytest.param(signal.SIGTERM, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
])
def test_signal_runner(tmp_config_file, all_paths, server_port, signal_num, new_event_loop):
    thread = Thread(target=raise_signal, args=(signal_num, '127.0.0.1', server_port))
    thread.start()
    run_server_default_tags(tmp_config_file, paths=all_paths)
    thread.join(timeout=1)


def modify_config_file(tmp_config_file, old_host, new_host):
    with open(str(tmp_config_file), "rt") as f:
        data = f.read()
        data = data.replace(old_host, new_host)
    with open(str(tmp_config_file), 'wt') as f:
        f.write(data)


def assert_reload_ok(signal_num, host, port, tmp_config_file, event):
    event.wait()
    event.clear()
    new_host = '127.0.0.2'
    assert not is_listening_on((new_host, port))
    modify_config_file(tmp_config_file, host, new_host)
    raise_signal(signal_num, host, port)
    event.wait()
    assert not is_listening_on((host, port))
    raise_signal(signal.SIGTERM, new_host, port)
    modify_config_file(tmp_config_file, host, new_host)


@pytest.mark.skip
@pytest.mark.parametrize('signal_num', [
    pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
])
def test_signal_runner_reload(tmp_config_file, all_paths, server_port, signal_num, new_event_loop):
    event = Event()
    thread = Thread(target=assert_reload_ok, args=(signal_num, '127.0.0.1', server_port, tmp_config_file, event))
    thread.start()

    def event_set(signum, frame):
        event.set()

    signal.signal(signal.SIGUSR2, event_set)
    run_server_default_tags(tmp_config_file, paths=all_paths, notify_pid=os.getpid())
    thread.join(timeout=1)
