from tests.test_receivers.conftest import *

from lib.senders.clients import BaseNetworkClient, TCPClient, UDPClient, pipe_client


@pytest.fixture
def tcp_client_one_way(protocol_factory_one_way_client, sock, peername) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_one_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                     srcport=0)


@pytest.fixture
def tcp_client_two_way(protocol_factory_two_way_client, sock, peername) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                     srcport=0)


@pytest.fixture
async def tcp_client_one_way_connected(server_started, protocol_factory_one_way_client, sock, peername) -> TCPClient:
    client = TCPClient(protocol_factory=protocol_factory_one_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                       srcport=0)
    async with client:
        yield client


@pytest.fixture
async def tcp_client_two_way_connected(server_started, protocol_factory_two_way_client, sock, peername) -> TCPClient:
    client = TCPClient(protocol_factory=protocol_factory_two_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                       srcport=0)
    async with client:
        yield client


@pytest.fixture
def udp_client_one_way(udp_protocol_factory_one_way_client, sock, peername) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_one_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                     srcport=0)


@pytest.fixture
def udp_client_two_way(udp_protocol_factory_two_way_client, sock, peername) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                     srcport=0)


@pytest.fixture
async def udp_client_one_way_connected(server_started, udp_protocol_factory_one_way_client, sock, peername) -> UDPClient:
    client = UDPClient(protocol_factory=udp_protocol_factory_one_way_client, host=sock[0], port=sock[1], srcip=peername[0],
                       srcport=0)
    async with client:
        yield client


@pytest.fixture
async def udp_client_two_way_connected(server_started, udp_protocol_factory_two_way_client, sock, peername) -> UDPClient:
    client = UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=sock[0], port=sock[1],
                       srcip=peername[0], srcport=0)
    async with client:
        yield client


@pytest.fixture
def pipe_client_one_way(protocol_factory_one_way_client, pipe_path):
    return pipe_client(protocol_factory=protocol_factory_one_way_client, path=pipe_path)


@pytest.fixture
async def pipe_client_one_way_connected(protocol_factory_one_way_client, pipe_path):
    client = pipe_client(protocol_factory=protocol_factory_one_way_client, path=pipe_path)
    async with client:
        yield client


@pytest.fixture
def pipe_client_two_way(protocol_factory_two_way_client, pipe_path):
    return pipe_client(protocol_factory=protocol_factory_two_way_client, path=pipe_path)


@pytest.fixture
async def pipe_client_two_way_connected(server_started, protocol_factory_two_way_client, pipe_path):
    client = pipe_client(protocol_factory=protocol_factory_two_way_client, path=pipe_path)
    async with client:
        yield client


@pytest.fixture
def server_started(receiver_sender_args):
    return receiver_sender_args[0]


@pytest.fixture
def client(receiver_sender_args) -> BaseNetworkClient:
    return receiver_sender_args[1]


@pytest.fixture
def client_connected(receiver_sender_args) -> BaseNetworkClient:
    return receiver_sender_args[2]


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_one_way_started.__name__, tcp_client_one_way.__name__, tcp_client_one_way_connected.__name__)),
    lazy_fixture(
        (tcp_server_two_way_started.__name__, tcp_client_two_way.__name__, tcp_client_two_way_connected.__name__)),
    pytest.param(
        lazy_fixture(
        (udp_server_one_way_started.__name__, udp_client_one_way.__name__, udp_client_one_way_connected.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture(
        (udp_server_two_way_started.__name__, udp_client_two_way.__name__, udp_client_two_way_connected.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way_started.__name__, pipe_client_one_way.__name__,
                      pipe_client_one_way_connected.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_two_way_started.__name__, pipe_client_two_way.__name__,
                      pipe_client_two_way_connected.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    )
])
def receiver_sender_args(request):
    return request.param