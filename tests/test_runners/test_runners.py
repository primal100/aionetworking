from aionetworking.runners import run_server_default_tags
import pytest
import signal
import time
import socket
import asyncio
import os
from aionetworking.compatibility import supports_keyboard_interrupt, py38
from threading import Thread


def port_is_open(host, port) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except:
        return False


def raise_signal(signal_num, host, port):
    time.sleep(1)
    assert port_is_open(host, port)
    if py38:
        signal.raise_signal(signal_num)
    else:
        os.kill(os.getpid(), signal_num)


@pytest.mark.parametrize('signal_num', [
    pytest.param(signal.SIGINT, marks=pytest.mark.skipif(not supports_keyboard_interrupt(), reason='Loop does not support keyboard interrupts')),
    pytest.param(signal.SIGTERM, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
])
def test_signal_runner(tmp_config_file, all_paths, server_port_load, signal_num, new_event_loop):
    thread = Thread(target=raise_signal, args=(signal_num, '127.0.0.1', server_port_load))
    thread.start()
    run_server_default_tags(tmp_config_file, paths=all_paths)
    thread.join(timeout=1)


def modify_config_file(tmp_config_file, old_host, new_host):
    with open(str(tmp_config_file), "rt") as f:
        data = f.read()
        data = data.replace(old_host, new_host)
    with open(str(tmp_config_file), 'wt') as f:
        f.write(data)


def assert_reload_ok(signal, host, port, tmp_config_file):
    time.sleep(1)
    new_host = '127.0.0.2'
    assert not port_is_open(new_host, port)
    modify_config_file(tmp_config_file, host, new_host)
    raise_signal(signal, host, port)
    time.sleep(1)
    assert not port_is_open(host, port)
    raise_signal(signal.SIGTERM, new_host, port)


@pytest.mark.parametrize('signal_num', [
    pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
])
def test_signal_runner_reload(tmp_config_file, all_paths, server_port_load, signal_num, new_event_loop):
    thread = Thread(target=assert_reload_ok, args=(signal_num, '127.0.0.1', server_port_load, tmp_config_file))
    thread.start()
    run_server_default_tags(tmp_config_file, paths=all_paths)
    thread.join(timeout=1)
