import socket
from tests.test_receivers.conftest import *

from lib.senders.clients import BaseNetworkClient, TCPClient, UDPClient, pipe_client
from lib.senders.sftp import SFTPClient


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
def udp_client_one_way(udp_protocol_factory_one_way_client, sock) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_one_way_client, host=sock[0], port=sock[1])


@pytest.fixture
def udp_client_two_way(udp_protocol_factory_two_way_client, sock) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=sock[0], port=sock[1])


@pytest.fixture
async def udp_client_one_way_connected(server_started, udp_client_one_way) -> UDPClient:
    async with udp_client_one_way:
        yield udp_client_one_way


@pytest.fixture
async def udp_client_two_way_connected(server_started, udp_client_two_way) -> UDPClient:
    async with udp_client_two_way:
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
def sftp_client(sftp_protocol_factory_client, sock, peername, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock[0], port=sock[1],
                      srcip=peername[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_exact_port(sftp_protocol_factory_client, sock, peername, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock[0], port=sock[1],
                      srcip=peername[0], srcport=60000, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_wrong_password(sftp_protocol_factory_client, sock, peername, sftp_username_password, patch_os_auth_failure) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock[0], port=sock[1],
                      srcip=peername[0], srcport=0, username=sftp_username_password[0],
                      password='abcdefgh')


@pytest.fixture
async def sftp_client_connected(server_started, sftp_client_one_way) -> SFTPClient:
    async with sftp_client_one_way:
        yield sftp_client_one_way


@pytest.fixture
def server_started(receiver_sender_args):
    return receiver_sender_args[0]


@pytest.fixture
def client(receiver_sender_args) -> BaseNetworkClient:
    return receiver_sender_args[1]


@pytest.fixture
def client_connected(receiver_sender_args) -> BaseNetworkClient:
    return receiver_sender_args[2]


@pytest.fixture
def server_context(receiver_sender_args) -> dict:
    return receiver_sender_args[3]


@pytest.fixture
def client_context(receiver_sender_args) -> dict:
    return receiver_sender_args[4]


if hasattr(socket, 'AF_UNIX'):
    @pytest.fixture
    def context_pipe_server() -> Dict[str, Any]:
        return {'protocol_name': 'TCP Server', 'endpoint': 'Unix Server /tmp/test', 'sock': '/tmp/test',
                'peer': '/tmp/test.1', 'alias': '/tmp/test.1', 'server': '/tmp/test', 'client': '/tmp/test.1',
                'fd': 1, 'own': '/tmp/test'}


    @pytest.fixture
    def context_pipe_client() -> Dict[str, Any]:
        return {'protocol_name': 'TCP Client', 'fd': 1, 'addr': '/tmp/test', 'own': '1',
                'peer': '/tmp/test.1', 'alias': '/tmp/test.1', 'server': '/tmp/test', 'client': '/tmp/test.1',
                }
else:
    @pytest.fixture
    def context_pipe_server(pipe_path) -> Dict[str, Any]:
        return {'protocol_name': 'TCP Server', 'endpoint': f'Windows Pipe Server {pipe_path}',
                'peer': '12345', 'alias': 12345, 'server':pipe_path, 'client': '12345',
                'handle': 12345, 'own': pipe_path}


    @pytest.fixture
    def context_pipe_client(pipe_path) -> Dict[str, Any]:
        return {'protocol_name': 'TCP Client', 'addr': str(pipe_path),
                'peer': f'{pipe_path}.12345', 'alias': 12346, 'server':str(pipe_path), 'client': '12345',
                'handle': 12346, 'own': '12345'}


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_one_way_started.__name__, tcp_client_one_way.__name__, tcp_client_one_way_connected.__name__,
         tcp_server_context.__name__, tcp_client_context.__name__)),
    lazy_fixture(
        (tcp_server_two_way_started.__name__, tcp_client_two_way.__name__, tcp_client_two_way_connected.__name__,
         tcp_server_context.__name__, tcp_client_context.__name__)),
    pytest.param(
        lazy_fixture(
            (udp_server_one_way_started.__name__, udp_client_one_way.__name__, udp_client_one_way_connected.__name__,
             udp_server_context.__name__, udp_client_context.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture(
            (udp_server_two_way_started.__name__, udp_client_two_way.__name__, udp_client_two_way_connected.__name__,
             udp_server_context.__name__, udp_client_context.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way_started.__name__, pipe_client_one_way.__name__,
                      pipe_client_one_way_connected.__name__, context_pipe_server.__name__, context_pipe_client.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_two_way_started.__name__, pipe_client_two_way.__name__,
                      pipe_client_two_way_connected.__name__, context_pipe_server.__name__, context_pipe_client.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    )
])
def receiver_sender_args(request):
    return request.param
