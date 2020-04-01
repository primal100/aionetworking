from __future__ import annotations

import datetime
import os
import pytest
import socket
import freezegun
from pathlib import Path
from aionetworking.utils import set_loop_policy, pipe_address_by_os
from aionetworking.types.networking import AFINETContext, AFUNIXContext, NamedPipeContext

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
    connection_marks = [mark for mark in metafunc.definition.iter_markers(name="connections")]
    if connection_marks:
        connection_args = connection_marks[0].args
        if not connection_args or connection_args == ('all',):
            connection_type_params = duplex_type_params = endpoint_params = 'all'
        else:
            connection_type_params, duplex_type_params, endpoint_params = connection_args[0].split('_')
        if connection_type_params == 'all':
            connection_type_params = ('tcp', 'udp', 'pipe')
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


@pytest.fixture
def tcp_server_context(server_sock_str, client_sock, client_hostname, client_sock_str) -> AFINETContext:
    context: AFINETContext = {
        'protocol_name': 'TCP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'address': client_sock[0], 'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': server_sock_str
    }
    return context


@pytest.fixture
def tcp_client_context(server_sock, server_sock_str, server_hostname, client_sock_str) -> AFINETContext:
    context: AFINETContext = {
        'protocol_name': 'TCP Client', 'host': server_hostname, 'port': server_sock[1], 'peer': server_sock_str,
        'address': server_sock[0], 'alias': f'{server_hostname}({server_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': client_sock_str
    }
    return context


@pytest.fixture
def udp_server_context(server_sock_str, client_sock, client_hostname, client_sock_str) -> AFINETContext:
    context: AFINETContext = {
        'protocol_name': 'UDP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'address': client_sock[0], 'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': server_sock_str
    }
    return context


@pytest.fixture
def udp_client_context(server_sock, server_sock_str, server_hostname, client_sock_str) -> AFINETContext:
    context: AFINETContext = {
        'protocol_name': 'UDP Client', 'host': server_hostname, 'port': server_sock[1], 'peer': server_sock_str,
        'address': server_sock[0], 'alias': f'{server_hostname}({server_sock_str})', 'server': server_sock_str,
        'client': client_sock_str, 'own': client_sock_str
    }
    return context


@pytest.fixture
def context(connection_type, endpoint, tcp_server_context, udp_server_context, tcp_client_context, udp_client_context,
            pipe_server_context, pipe_client_context) -> Dict[str, Any]:
    contexts = {
        'tcp': {
            'server': tcp_server_context,
            'client': tcp_client_context
        },
        'udp': {
            'server': udp_server_context,
            'client': udp_client_context
        },
        'pipe': {
            'server': pipe_server_context,
            'client': pipe_client_context
        }
    }
    return contexts[connection_type][endpoint]


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
