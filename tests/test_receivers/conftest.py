import pytest
from lib.receivers.servers import TCPServer, pipe_server

from tests.test_networking.conftest import *
from lib.utils import pipe_address_by_os
from pytest_lazyfixture import lazy_fixture


@pytest.fixture
async def pipe_path() -> Path:
    path = pipe_address_by_os()
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
async def tcp_server_one_way(protocol_factory_one_way_server, sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_one_way_server, host=sock[0], port=sock[1])
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_one_way_quiet(tcp_server_one_way) -> TCPServer:
    tcp_server_one_way.quiet = True
    yield tcp_server_one_way


@pytest.fixture
async def tcp_server_one_way_started(tcp_server_one_way) -> TCPServer:
    await tcp_server_one_way.start()
    yield tcp_server_one_way


@pytest.fixture
async def pipe_server_one_way(protocol_factory_one_way_server, pipe_path) -> BaseServer:
    server = pipe_server(protocol_factory=protocol_factory_one_way_server, path=pipe_path)
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def pipe_server_one_way_quiet(pipe_server_one_way) -> BaseServer:
    pipe_server_one_way.quiet = True
    yield pipe_server_one_way


@pytest.fixture
async def pipe_server_one_way_started(pipe_server_one_way) -> BaseServer:
    await pipe_server_one_way.start()
    yield pipe_server_one_way


@pytest.fixture
def server_receiver(receiver_args) -> BaseServer:
    return receiver_args[0]


@pytest.fixture
def server_started(receiver_args) -> BaseServer:
    return receiver_args[1]


@pytest.fixture
def server_quiet(receiver_args) -> BaseServer:
    return receiver_args[2]


server_client_params = [
    lazy_fixture((tcp_server_one_way.__name__,)),
    pytest.param(
        lazy_fixture((pipe_server_one_way.__name__,)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
]
@pytest.fixture(params=server_client_params)
def server_args(request) -> Tuple:
    return request.param


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_one_way.__name__, tcp_server_one_way_started.__name__, tcp_server_one_way_quiet.__name__)) + [True],
    lazy_fixture(
        (tcp_server_one_way.__name__, tcp_server_one_way_started.__name__, tcp_server_one_way_quiet.__name__)) + [
        False],
    pytest.param(
        lazy_fixture((pipe_server_one_way.__name__, pipe_server_one_way_started.__name__,
                      pipe_server_one_way_quiet.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way.__name__, pipe_server_one_way_started.__name__,
                      pipe_server_one_way_quiet.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    )])
def receiver_args(request):
    return request.param
