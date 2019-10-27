import socket
from tests.test_receivers.conftest import *

from lib.senders.clients import BaseNetworkClient, TCPClient, UDPClient, pipe_client
from lib.senders.sftp import SFTPClient


@pytest.fixture
def tcp_client_one_way(protocol_factory_one_way_client, sock, peer) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_one_way_client, host=sock[0], port=sock[1], srcip=peer[0],
                     srcport=0)


@pytest.fixture
def tcp_client_two_way(protocol_factory_two_way_client, sock, peer) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=sock[0], port=sock[1], srcip=peer[0],
                     srcport=0)


@pytest.fixture
def tcp_client_two_way_ipv6(protocol_factory_two_way_client, sock_ipv6, peer_ipv6) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=sock_ipv6[0], port=sock_ipv6[1],
                     srcip=peer_ipv6[0], srcport=0)


@pytest.fixture
def tcp_client_two_way_ssl(protocol_factory_two_way_client, sock, peer, client_side_ssl) -> TCPClient:
    client_side_ssl.check_hostname = False
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=sock[0], port=sock[1], srcip=peer[0],
                     srcport=0, ssl=client_side_ssl)


@pytest.fixture
def tcp_client_two_way_ssl_no_cadata(protocol_factory_two_way_client, sock, peer, client_side_ssl_no_cadata) -> TCPClient:
    client_side_ssl.check_hostname = False
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=sock[0], port=sock[1], srcip=peer[0],
                     srcport=0, ssl=client_side_ssl_no_cadata, ssl_handshake_timeout=60)


@pytest.fixture
async def tcp_client_one_way_connected(tcp_client_one_way) -> TCPClient:
    async with tcp_client_one_way:
        yield tcp_client_one_way


@pytest.fixture
async def tcp_client_two_way_connected(tcp_client_two_way) -> TCPClient:
    async with tcp_client_two_way:
        yield tcp_client_two_way


@pytest.fixture
async def tcp_client_two_way_connected_ssl(tcp_client_two_way_ssl):
    async with tcp_server_two_way_ssl:
        yield tcp_server_two_way_ssl


@pytest.fixture
def udp_client_one_way(udp_protocol_factory_one_way_client, sock) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_one_way_client, host=sock[0], port=sock[1])


@pytest.fixture
def udp_client_two_way(udp_protocol_factory_two_way_client, sock) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=sock[0], port=sock[1])


@pytest.fixture
def udp_client_two_way_ipv6(udp_protocol_factory_two_way_client, sock_ipv6) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=sock_ipv6[0], port=sock_ipv6[1])


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
def sftp_client(sftp_protocol_factory_client, sock, peer, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock[0], port=sock[1],
                      srcip=peer[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_ipv6(sftp_protocol_factory_client, sock_ipv6, peer_ipv6, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock_ipv6[0], port=sock_ipv6[1],
                      srcip=peer_ipv6[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_exact_port(sftp_protocol_factory_client, sock, peer, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock[0], port=sock[1],
                      srcip=peer[0], srcport=peer[1], username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_wrong_password(sftp_protocol_factory_client, sock, peer, sftp_username_password, patch_os_auth_failure) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=sock[0], port=sock[1],
                      srcip=peer[0], srcport=0, username=sftp_username_password[0],
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
    lazy_fixture(
        (tcp_server_two_way_ssl_started.__name__, tcp_client_two_way_ssl.__name__, tcp_client_two_way_connected_ssl.__name__,
         tcp_server_context_ssl.__name__, tcp_client_context_ssl.__name__)),
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


@pytest.fixture
async def protocol_factory_allowed_senders_server(echo_action, initial_server_context, peer, peer_ipv6) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork(peer[0]), IPNetwork(peer_ipv6[0])]
    )
    yield factory


@pytest.fixture
async def protocol_factory_allowed_senders_server_wrong_senders(echo_action, initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork('127.0.0.2'), IPNetwork('::2')]
    )
    yield factory


@pytest.fixture
async def tcp_server_allowed_senders_ipv4(protocol_factory_allowed_senders_server, sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server, host=sock[0], port=sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_allowed_senders_ipv6(protocol_factory_allowed_senders_server, sock_ipv6) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server, host=sock_ipv6[0], port=sock_ipv6[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_allowed_senders_ipv4_wrong_senders(protocol_factory_allowed_senders_server_wrong_senders, sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server_wrong_senders, host=sock[0], port=sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_allowed_senders_ipv6_wrong_senders(protocol_factory_allowed_senders_server_wrong_senders, sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server_wrong_senders, host='::1', port=sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def udp_protocol_factory_allowed_senders_wrong_senders(echo_action) -> DatagramServerProtocolFactory:
    factory = DatagramServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork('127.0.0.2'), IPNetwork('::2')])
    await factory.start()
    yield factory
    await factory.close()


@pytest.fixture
async def udp_server_allowed_senders_ipv4(udp_protocol_factory_allowed_senders, sock) -> UDPServer:
    yield UDPServer(protocol_factory=udp_protocol_factory_allowed_senders, host=sock[0], port=sock[1])


@pytest.fixture
async def udp_server_allowed_senders_ipv4_started(udp_server_allowed_senders_ipv4) -> UDPServer:
    await udp_server_allowed_senders_ipv4.start()
    yield udp_server_allowed_senders_ipv4
    if udp_server_allowed_senders_ipv4.is_started():
        await udp_server_allowed_senders_ipv4.close()


@pytest.fixture
async def udp_server_allowed_senders_ipv6(udp_protocol_factory_allowed_senders, sock_ipv6) -> UDPServer:
    yield UDPServer(protocol_factory=udp_protocol_factory_allowed_senders, host=sock_ipv6[0], port=sock_ipv6[1])


@pytest.fixture
async def udp_server_allowed_senders_ipv6_started(udp_server_allowed_senders_ipv6) -> UDPServer:
    await udp_server_allowed_senders_ipv6.start()
    yield udp_server_allowed_senders_ipv6
    if udp_server_allowed_senders_ipv6.is_started():
        await udp_server_allowed_senders_ipv6.close()


@pytest.fixture
async def udp_server_allowed_senders_wrong_senders_ipv4(udp_protocol_factory_allowed_senders_wrong_senders, sock) -> UDPServer:
    server = UDPServer(protocol_factory=udp_protocol_factory_allowed_senders_wrong_senders, host=sock[0], port=sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def udp_server_allowed_senders_wrong_senders_ipv6(udp_protocol_factory_allowed_senders_wrong_senders, sock_ipv6) -> UDPServer:
    server = UDPServer(protocol_factory=udp_protocol_factory_allowed_senders_wrong_senders, host=sock_ipv6[0], port=sock_ipv6[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
def tcp_server_started_allowed_senders(tcp_allowed_senders_ok_args) -> TCPServer:
    return tcp_allowed_senders_ok_args[0]


@pytest.fixture
def tcp_client_allowed_senders(tcp_allowed_senders_ok_args) -> TCPClient:
    return tcp_allowed_senders_ok_args[1]


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_allowed_senders_ipv4.__name__, tcp_client_two_way.__name__)),
    lazy_fixture(
        (tcp_server_allowed_senders_ipv6.__name__, tcp_client_two_way_ipv6.__name__)),
])
def tcp_allowed_senders_ok_args(request):
    return request.param


@pytest.fixture
def udp_server_started_allowed_senders(udp_allowed_senders_ok_args) -> TCPServer:
    return udp_allowed_senders_ok_args[0]


@pytest.fixture
def udp_client_allowed_senders(udp_allowed_senders_ok_args) -> TCPClient:
    return udp_allowed_senders_ok_args[1]


@pytest.fixture(params=[
    pytest.param(
        lazy_fixture(
            (udp_server_allowed_senders_ipv4_started.__name__, udp_client_two_way.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture(
            (udp_server_allowed_senders_ipv6_started.__name__, udp_client_two_way_ipv6.__name__)),
        marks=pytest.mark.skipif(
            "is_proactor()")
    )
])
def udp_allowed_senders_ok_args(request):
    return request.param


@pytest.fixture
def tcp_server_started_wrong_senders(tcp_allowed_senders_not_ok_args) -> TCPServer:
    return tcp_allowed_senders_not_ok_args[0]


@pytest.fixture
def tcp_client_wrong_senders(tcp_allowed_senders_not_ok_args) -> TCPClient:
    return tcp_allowed_senders_not_ok_args[1]


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_allowed_senders_ipv4_wrong_senders.__name__, tcp_client_two_way.__name__)),
    lazy_fixture(
        (tcp_server_allowed_senders_ipv6_wrong_senders.__name__, tcp_client_two_way_ipv6.__name__)),
])
def tcp_allowed_senders_not_ok_args(request):
    return request.param


@pytest.fixture
def udp_server_started_wrong_senders(udp_allowed_senders_not_ok_args) -> TCPServer:
    return udp_allowed_senders_not_ok_args[0]


@pytest.fixture
def udp_client_wrong_senders(udp_allowed_senders_not_ok_args) -> TCPClient:
    return udp_allowed_senders_not_ok_args[1]


@pytest.fixture(params=[
    pytest.param(
        lazy_fixture(
            (udp_server_allowed_senders_wrong_senders_ipv4.__name__, udp_client_two_way.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture(
            (udp_server_allowed_senders_wrong_senders_ipv6.__name__, udp_client_two_way_ipv6.__name__)),
        marks=pytest.mark.skipif(
            "is_proactor()")
    )
])
def udp_allowed_senders_not_ok_args(request):
    return request.param


@pytest.fixture
async def sftp_protocol_factory_server_allowed_senders(buffered_file_storage_action, peer, peer_ipv6) -> SFTPOSAuthProtocolFactory:
    factory = SFTPOSAuthProtocolFactory(
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork(peer[0]), IPNetwork(peer_ipv6[0])]
    )
    yield factory


@pytest.fixture
async def sftp_protocol_factory_server_not_allowed_senders(buffered_file_storage_action) -> SFTPOSAuthProtocolFactory:
    factory = SFTPOSAuthProtocolFactory(
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork('127.0.0.2'), IPNetwork('::2')]
    )
    yield factory


@pytest.fixture
async def sftp_server_allowed_senders_ip4(sftp_protocol_factory_server_allowed_senders, sock, tmp_path, ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_allowed_senders, host=sock[0], port=sock[1],
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_allowed_senders_ipv6(sftp_protocol_factory_server_allowed_senders, sock_ipv6, tmp_path, ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_allowed_senders, host=sock_ipv6[0], port=sock_ipv6[1],
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_not_allowed_senders_ip4(sftp_protocol_factory_server_not_allowed_senders, sock, tmp_path,
                                              ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_not_allowed_senders, host=sock[0], port=sock[1],
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_not_allowed_senders_ipv6(sftp_protocol_factory_server_not_allowed_senders, sock_ipv6, tmp_path,
                                               ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_not_allowed_senders, host=sock_ipv6[0], port=sock_ipv6[1],
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture(params=[
    lazy_fixture(
        (sftp_server_allowed_senders_ip4.__name__, sftp_client.__name__)),
    lazy_fixture(
        (sftp_server_allowed_senders_ipv6.__name__, sftp_client_ipv6.__name__)),
])
def sftp_allowed_senders_ok_args(request):
    return request.param


@pytest.fixture(params=[
        lazy_fixture(
            (sftp_server_not_allowed_senders_ip4.__name__, sftp_client.__name__)),
        lazy_fixture(
            (sftp_server_not_allowed_senders_ipv6.__name__, sftp_client_ipv6.__name__))
])
def sftp_allowed_senders_not_ok_args(request):
    return request.param


@pytest.fixture
def sftp_server_started_allowed_senders(sftp_allowed_senders_ok_args) -> SFTPServer:
    return sftp_allowed_senders_ok_args[0]


@pytest.fixture
def sftp_client_allowed_senders(sftp_allowed_senders_ok_args) -> SFTPClient:
    return sftp_allowed_senders_ok_args[1]


@pytest.fixture
def sftp_server_started_wrong_senders(sftp_allowed_senders_not_ok_args) -> SFTPServer:
    return sftp_allowed_senders_not_ok_args[0]


@pytest.fixture
def sftp_client_wrong_senders(sftp_allowed_senders_not_ok_args) -> SFTPClient:
    return sftp_allowed_senders_not_ok_args[1]