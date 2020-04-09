from __future__ import annotations

import datetime
import os
import pytest
import socket
import freezegun
from pathlib import Path
from aionetworking.compatibility import supports_pipe_or_unix_connections, datagram_supported
from aionetworking.utils import set_loop_policy, pipe_address_by_os
from aionetworking.types.networking import AFINETContext, AFUNIXContext, NamedPipeContext, SFTPContext

from typing import Dict, Any


def pytest_addoption(parser):
    default = 'proactor' if os.name == 'nt' else 'selector'
    choices = ('selector', 'uvloop') if os.name == 'linux' else ('proactor', 'selector')
    parser.addoption(
        "--loop",
        action="store",
        default=default,
        help=f"Loop to use. Choices are: {','.join(choices)}",
    )


def pytest_configure(config):
    loop_type = config.getoption("--loop")
    if loop_type:
        set_loop_policy(linux_loop_type=loop_type, windows_loop_type=loop_type)


def pytest_generate_tests(metafunc):
    skipifwindowsxdist_marks = [mark for mark in metafunc.definition.iter_markers(name="skipifwindowsxdist")]
    if skipifwindowsxdist_marks:
        if hasattr(metafunc.config, 'slaveinput'):
            pytest.skip("Test doesn't work correctly in windows with xdist")
    connection_marks = [mark for mark in metafunc.definition.iter_markers(name="connections")]
    if connection_marks:
        connection_args = connection_marks[0].args
        if not connection_args or connection_args == ('all',):
            connection_type_params = duplex_type_params = endpoint_params = 'all'
        else:
            connection_type_params, duplex_type_params, endpoint_params = connection_args[0].split('_')
        if connection_type_params == 'all':
            connection_type_params = ['tcp']
            if datagram_supported():
                connection_type_params.append('udp')
            if supports_pipe_or_unix_connections():
                connection_type_params.append('pipe')
        elif connection_type_params == 'allplus':
            connection_type_params = ['tcp', 'tcpssl', 'sftp']
            if datagram_supported():
                connection_type_params.append('udp')
            if supports_pipe_or_unix_connections():
                connection_type_params.append('pipe')
        elif connection_type_params == 'sslsftp':
            connection_type_params = ['tcpssl', 'sftp']
        elif connection_type_params == 'inet':
            connection_type_params = ['tcp']
            if datagram_supported():
                connection_type_params.append('udp')
        else:
            connection_type_params = (connection_type_params,)
        if duplex_type_params == 'all':
            duplex_type_params = ('oneway', 'twoway')
        else:
            duplex_type_params = (duplex_type_params,)
        if endpoint_params == 'all':
            endpoint_params = ('server', 'client')
        else:
            endpoint_params = (endpoint_params,)
    else:
        connection_type_params = ['tcp']
        duplex_type_params = ['oneway']
        endpoint_params = ['server']
    if 'connection_type' in metafunc.fixturenames:
        metafunc.parametrize('connection_type', connection_type_params)
    if 'duplex_type' in metafunc.fixturenames:
        metafunc.parametrize('duplex_type', duplex_type_params)
    if 'endpoint' in metafunc.fixturenames:
        metafunc.parametrize('endpoint', endpoint_params)


@pytest.fixture
def connection_type(request) -> str:
    return request.param


@pytest.fixture
def duplex_type(request) -> str:
    return request.param


@pytest.fixture
def endpoint(request) -> str:
    return request.param


@pytest.fixture
def timestamp() -> datetime.datetime:
    return datetime.datetime(2019, 1, 1, 1, 1)


@pytest.fixture
def fixed_timestamp(timestamp) -> datetime.datetime:
    freezer = freezegun.freeze_time(timestamp)
    freezer.start()
    yield datetime.datetime.now()
    freezer.stop()


@pytest.fixture
def pipe_path(server_port) -> Path:
    if os.name == 'linux':
        path = Path(f'/tmp/test_{server_port}')
    else:
        path = pipe_address_by_os()
    yield path
    if path.exists():
        path.unlink()


def _tcp_server_context(server_sock, client_sock, client_hostname) -> AFINETContext:
    client_sock_str = f'{client_sock[0]}:{client_sock[1]}'
    server_sock_str = f'{server_sock[0]}:{server_sock[1]}'
    context: AFINETContext = {
        'protocol_name': 'TCP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'address': client_sock[0], 'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': server_sock_str
    }
    return context


@pytest.fixture
def tcp_server_context_fixed_port(server_sock, client_sock, client_hostname) -> AFINETContext:
    return _tcp_server_context(server_sock, client_sock, client_hostname)


@pytest.fixture
def tcp_server_context_actual_port(actual_server_sock, actual_client_sock, client_hostname) -> AFINETContext:
    return _tcp_server_context(actual_server_sock, actual_client_sock, client_hostname)


def _tcp_client_context(server_sock, client_sock, server_hostname) -> AFINETContext:
    client_sock_str = f'{client_sock[0]}:{client_sock[1]}'
    server_sock_str = f'{server_sock[0]}:{server_sock[1]}'
    context: AFINETContext = {
        'protocol_name': 'TCP Client', 'host': server_hostname, 'port': server_sock[1], 'peer': server_sock_str,
        'address': server_sock[0], 'alias': f'{server_hostname}({server_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': client_sock_str
    }
    return context


@pytest.fixture
def tcp_client_context_fixed_port(server_sock, client_sock, client_hostname) -> AFINETContext:
    return _tcp_client_context(server_sock, client_sock, client_hostname)


@pytest.fixture
def tcp_client_context_actual_port(actual_server_sock, actual_client_sock, client_hostname) -> AFINETContext:
    return _tcp_client_context(actual_server_sock, actual_client_sock, client_hostname)


def _udp_server_context(server_sock, client_sock, client_hostname) -> AFINETContext:
    client_sock_str = f'{client_sock[0]}:{client_sock[1]}'
    server_sock_str = f'{server_sock[0]}:{server_sock[1]}'
    context: AFINETContext = {
        'protocol_name': 'UDP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'address': client_sock[0], 'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': server_sock_str
    }
    return context


@pytest.fixture
def udp_server_context_fixed_port(server_sock, client_sock, client_hostname) -> AFINETContext:
    return _udp_server_context(server_sock, client_sock, client_hostname)


@pytest.fixture
def udp_server_context_actual_port(actual_server_sock, actual_client_sock, client_hostname) -> AFINETContext:
    return _udp_server_context(actual_server_sock, actual_client_sock, client_hostname)


def _udp_client_context(server_sock, client_sock, server_hostname) -> AFINETContext:
    client_sock_str = f'{client_sock[0]}:{client_sock[1]}'
    server_sock_str = f'{server_sock[0]}:{server_sock[1]}'
    context: AFINETContext = {
        'protocol_name': 'UDP Client', 'host': server_hostname, 'port': server_sock[1], 'peer': server_sock_str,
        'address': server_sock[0], 'alias': f'{server_hostname}({server_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': client_sock_str
    }
    return context


@pytest.fixture
def udp_client_context_fixed_port(server_sock, client_sock, client_hostname) -> AFINETContext:
    return _udp_client_context(server_sock, client_sock, client_hostname)


@pytest.fixture
def udp_client_context_actual_port(actual_server_sock, actual_client_sock, client_hostname) -> AFINETContext:
    return _udp_client_context(actual_server_sock, actual_client_sock, client_hostname)


@pytest.fixture
def context(connection_type, endpoint, tcp_server_context_fixed_port, tcp_client_context_fixed_port,
            udp_server_context_fixed_port, udp_client_context_fixed_port, pipe_server_context,
            pipe_client_context, sftp_server_context_fixed_port, sftp_client_context_fixed_port) -> Dict[str, Any]:
    contexts = {
        'tcp': {
            'server': tcp_server_context_fixed_port,
            'client': tcp_client_context_fixed_port
        },
        'tcpssl': {
            'server': tcp_server_context_fixed_port,
            'client': tcp_client_context_fixed_port
        },
        'udp': {
            'server': udp_server_context_fixed_port,
            'client': udp_client_context_fixed_port
        },
        'pipe': {
            'server': pipe_server_context,
            'client': pipe_client_context
        },
        'sftp': {
            'server': sftp_server_context_fixed_port,
            'client': sftp_client_context_fixed_port
        }
    }
    return contexts[connection_type][endpoint]


@pytest.fixture
def server_context(connection_type, tcp_server_context_actual_port, udp_server_context_actual_port, pipe_server_context, sftp_server_context_actual_port) -> Dict[str, Any]:
    contexts = {
        'tcp': tcp_server_context_actual_port,
        'tcpssl': tcp_server_context_actual_port,
        'udp': udp_server_context_actual_port,
        'pipe': pipe_server_context,
        'sftp': sftp_server_context_actual_port
    }
    return contexts[connection_type]


@pytest.fixture
def server_context_fixed_port(connection_type, tcp_server_context_fixed_port, udp_server_context_fixed_port, pipe_server_context, sftp_server_context_fixed_port) -> Dict[str, Any]:
    contexts = {
        'tcp': tcp_server_context_fixed_port,
        'tcpssl': tcp_server_context_fixed_port,
        'udp': udp_server_context_fixed_port,
        'pipe': pipe_server_context,
        'sftp': sftp_server_context_fixed_port
    }
    return contexts[connection_type]


@pytest.fixture
def client_context(connection_type, tcp_client_context_actual_port, udp_client_context_actual_port, pipe_client_context, sftp_client_context_actual_port) -> Dict[str, Any]:
    contexts = {
        'tcp': tcp_client_context_actual_port,
        'tcpssl': tcp_client_context_actual_port,
        'udp': udp_client_context_actual_port,
        'pipe': pipe_client_context,
        'sftp': sftp_client_context_actual_port
    }
    return contexts[connection_type]


if hasattr(socket, 'AF_UNIX'):
    @pytest.fixture
    def pipe_server_context(pipe_path) -> AFUNIXContext:
        context: AFUNIXContext = {
            'protocol_name': 'Unix Server', 'address': Path(pipe_path).name, 'peer': '1', 'own': str(pipe_path),
            'alias': '/tmp/test.1', 'server': pipe_path, 'client': '1', 'fd': 1,
        }
        return context

    @pytest.fixture
    def pipe_client_context(pipe_path) -> AFUNIXContext:
        context: AFUNIXContext = {
            'protocol_name': 'Unix Client', 'address': Path(pipe_path).name, 'peer': str(pipe_path), 'own': '1',
            'alias': f'{pipe_path}.1', 'server': str(pipe_path), 'client': '1', 'fd': 1
        }
        return context
else:
    @pytest.fixture
    def pipe_server_context(pipe_path) -> NamedPipeContext:
        context: NamedPipeContext = {
            'protocol_name': 'PIPE Server', 'address': pipe_path.name, 'peer': '12345',  'own': str(pipe_path),
            'alias': f'{pipe_path}.12345', 'server': str(pipe_path), 'client': '12345', 'handle': 12345,
        }
        return context

    @pytest.fixture
    def pipe_client_context(pipe_path) -> NamedPipeContext:
        context: NamedPipeContext = {
            'protocol_name': 'PIPE Client', 'address': pipe_path.name, 'peer': str(pipe_path), 'own': '12346',
            'alias': f'{pipe_path}.12346', 'server':str(pipe_path), 'client': '12346', 'handle': 12346
        }
        return context


@pytest.fixture
def sftp_server_context(server_sock_str, client_sock, client_hostname, client_sock_str) -> SFTPContext:
    context: SFTPContext = {
        'protocol_name': 'SFTP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'address': client_sock[0], 'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': server_sock_str, 'username': 'testuser'
    }
    return context


@pytest.fixture
def sftp_client_context(server_sock, server_sock_str, server_hostname, client_sock_str) -> SFTPContext:
    context: SFTPContext = {
        'protocol_name': 'SFTP Client', 'host': server_hostname, 'port': server_sock[1], 'peer': server_sock_str,
        'address': server_sock[0], 'alias': f'{server_hostname}({server_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': client_sock_str, 'username': 'testuser'
    }
    return context


@pytest.fixture
def sftp_username() -> str:
    return 'testuser'


def _sftp_server_context(server_sock, client_sock, client_hostname, sftp_username) -> SFTPContext:
    client_sock_str = f'{client_sock[0]}:{client_sock[1]}'
    server_sock_str = f'{server_sock[0]}:{server_sock[1]}'
    context: SFTPContext = {
        'protocol_name': 'SFTP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'address': client_sock[0], 'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': server_sock_str, 'username': sftp_username
    }
    return context


@pytest.fixture
def sftp_server_context_fixed_port(server_sock, client_sock, client_hostname, sftp_username) -> SFTPContext:
    return _sftp_server_context(server_sock, client_sock, client_hostname, sftp_username)


@pytest.fixture
def sftp_server_context_actual_port(actual_server_sock, actual_client_sock, client_hostname, sftp_username) -> SFTPContext:
    return _sftp_server_context(actual_server_sock, actual_client_sock, client_hostname, sftp_username)


def _sftp_client_context(server_sock, client_sock, server_hostname, sftp_username) -> SFTPContext:
    client_sock_str = f'{client_sock[0]}:{client_sock[1]}'
    server_sock_str = f'{server_sock[0]}:{server_sock[1]}'
    context: SFTPContext = {
        'protocol_name': 'SFTP Client', 'host': server_hostname, 'port': server_sock[1], 'peer': server_sock_str,
        'address': server_sock[0], 'alias': f'{server_hostname}({server_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': client_sock_str, 'username': sftp_username
    }
    return context


@pytest.fixture
def sftp_client_context_fixed_port(server_sock, client_sock, client_hostname, sftp_username) -> SFTPContext:
    return _sftp_client_context(server_sock, client_sock, client_hostname, sftp_username)


@pytest.fixture
def sftp_client_context_actual_port(actual_server_sock, actual_client_sock, client_hostname, sftp_username) -> SFTPContext:
    return _sftp_client_context(actual_server_sock, actual_client_sock, client_hostname, sftp_username)
