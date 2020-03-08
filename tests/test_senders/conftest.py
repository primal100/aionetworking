import socket
from tests.test_receivers.conftest import *

from aionetworking import TCPClient, UDPClient, pipe_client
from aionetworking.senders import BaseNetworkClient
from aionetworking.senders.sftp import SFTPClient

from aionetworking.types.networking import AFUNIXContext, NamedPipeContext


@pytest.fixture
def tcp_client_one_way(protocol_factory_one_way_client, server_sock, client_sock) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_one_way_client, host=server_sock[0], port=server_sock[1], srcip=client_sock[0],
                     srcport=0)


@pytest.fixture
def tcp_client_two_way(protocol_factory_two_way_client, server_sock, client_sock) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=server_sock[0], port=server_sock[1],
                     srcip=client_sock[0], srcport=0)


@pytest.fixture
def tcp_client_two_way_two(protocol_factory_two_way_client, server_sock, client_sock) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=server_sock[0], port=server_sock[1],
                     srcip=client_sock[0], srcport=0)


@pytest.fixture
def tcp_client_two_way_ipv6(protocol_factory_two_way_client, server_sock_ipv6, client_sock_ipv6) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=server_sock_ipv6[0], port=server_sock_ipv6[1],
                     srcip=client_sock_ipv6[0], srcport=0)


@pytest.fixture
def tcp_client_two_way_ssl(protocol_factory_two_way_client, server_sock, client_sock, client_side_ssl) -> TCPClient:
    client_side_ssl.check_hostname = False
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=server_sock[0], port=server_sock[1], srcip=client_sock[0],
                     srcport=0, ssl=client_side_ssl)


@pytest.fixture
def tcp_client_two_way_ssl_no_cadata(protocol_factory_two_way_client, server_sock, client_sock, client_side_ssl_no_cadata) -> TCPClient:
    client_side_ssl.check_hostname = False
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=server_sock[0], port=server_sock[1], srcip=client_sock[0],
                     srcport=0, ssl=client_side_ssl_no_cadata, ssl_handshake_timeout=60)


@pytest.fixture
def udp_client_one_way(udp_protocol_factory_one_way_client, server_sock) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_one_way_client, host=server_sock[0], port=server_sock[1])


@pytest.fixture
def udp_client_two_way(udp_protocol_factory_two_way_client, server_sock) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=server_sock[0], port=server_sock[1])


@pytest.fixture
def udp_client_two_way_ipv6(udp_protocol_factory_two_way_client, server_sock_ipv6) -> UDPClient:
    return UDPClient(protocol_factory=udp_protocol_factory_two_way_client, host=server_sock_ipv6[0], port=server_sock_ipv6[1])


@pytest.fixture
def pipe_client_one_way(protocol_factory_one_way_client, pipe_path):
    return pipe_client(protocol_factory=protocol_factory_one_way_client, path=pipe_path)


@pytest.fixture
def pipe_client_two_way(protocol_factory_two_way_client_pipe, pipe_path):
    return pipe_client(protocol_factory=protocol_factory_two_way_client_pipe, path=pipe_path)


@pytest.fixture
def sftp_client(sftp_protocol_factory_client, server_sock, client_sock, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=server_sock[0], port=server_sock[1],
                      srcip=client_sock[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_ipv6(sftp_protocol_factory_client, server_sock_ipv6, client_sock_ipv6, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=server_sock_ipv6[0], port=server_sock_ipv6[1],
                      srcip=client_sock_ipv6[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_exact_port(sftp_protocol_factory_client, server_sock, client_sock, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=server_sock[0], port=server_sock[1],
                      srcip=client_sock[0], srcport=client_sock[1], username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_wrong_password(sftp_protocol_factory_client, server_sock, client_sock, sftp_username_password, patch_os_auth_failure) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=server_sock[0], port=server_sock[1],
                      srcip=client_sock[0], srcport=0, username=sftp_username_password[0],
                      password='abcdefgh')


@pytest.fixture
def server_started(receiver_sender_args):
    return receiver_sender_args[0]


@pytest.fixture
def client(receiver_sender_args) -> BaseNetworkClient:
    return receiver_sender_args[1]


@pytest.fixture
def server_context(receiver_sender_args) -> dict:
    return receiver_sender_args[2]


@pytest.fixture
def client_context(receiver_sender_args) -> dict:
    return receiver_sender_args[3]


if hasattr(socket, 'AF_UNIX'):
    @pytest.fixture
    def context_pipe_server(pipe_path) -> AFUNIXContext:
        context: AFUNIXContext = {
            'protocol_name': 'Unix Server', 'address': pipe_path.name, 'peer': '1', 'own': str(pipe_path),
            'alias': '/tmp/test.1', 'server': str(pipe_path), 'client': '1', 'fd': 1,
        }
        return context

    @pytest.fixture
    def context_pipe_client(pipe_path) -> AFUNIXContext:
        context: AFUNIXContext = {
            'protocol_name': 'Unix Client', 'address': pipe_path.name, 'peer': str(pipe_path), 'own': '1',
            'alias': f'{pipe_path}.1', 'server': str(pipe_path), 'client': '1', 'fd': 1
        }
        return context
else:
    @pytest.fixture
    def context_pipe_server(pipe_path) -> NamedPipeContext:
        context: NamedPipeContext = {
            'protocol_name': 'Pipe Server', 'address': pipe_path.name, 'peer': '12345',  'own': str(pipe_path),
            'alias': f'{pipe_path}.12345', 'server': str(pipe_path), 'client': '12345', 'handle': 12345,
        }
        return context

    @pytest.fixture
    def context_pipe_client(pipe_path) -> NamedPipeContext:
        context: NamedPipeContext = {
            'protocol_name': 'Pipe Client', 'address': str(pipe_path), 'peer': '12345', 'own': '12345',
            'alias': f'{pipe_path}.12346', 'server':str(pipe_path), 'client': '12345', 'handle': 12346
        }
        return context


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_one_way_started.__name__, tcp_client_one_way.__name__,
         tcp_server_context.__name__, tcp_client_context.__name__)),
    lazy_fixture(
        (tcp_server_two_way_started.__name__, tcp_client_two_way.__name__,
         tcp_server_context.__name__, tcp_client_context.__name__)),
    lazy_fixture(
        (tcp_server_two_way_ssl_started.__name__, tcp_client_two_way_ssl.__name__,
         tcp_server_context.__name__, tcp_client_context.__name__)),
    pytest.param(
        lazy_fixture(
            (udp_server_one_way_started.__name__, udp_client_one_way.__name__,
             udp_server_context.__name__, udp_client_context.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture(
            (udp_server_two_way_started.__name__, udp_client_two_way.__name__,
             udp_server_context.__name__, udp_client_context.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way_started.__name__, pipe_client_one_way.__name__,
                      context_pipe_server.__name__, context_pipe_client.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_two_way_started.__name__, pipe_client_two_way.__name__,
                      context_pipe_server.__name__, context_pipe_client.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    )
])
def receiver_sender_args(request):
    return request.param


@pytest.fixture
async def protocol_factory_allowed_senders_server(echo_action, initial_server_context, client_sock, client_sock_ipv6) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork(client_sock[0]), IPNetwork(client_sock_ipv6[0])]
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
async def tcp_server_allowed_senders_ipv4(protocol_factory_allowed_senders_server, server_sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server, host=server_sock[0], port=server_sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_allowed_senders_ipv6(protocol_factory_allowed_senders_server, server_sock_ipv6) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server, host=server_sock_ipv6[0], port=server_sock_ipv6[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_allowed_senders_ipv4_wrong_senders(protocol_factory_allowed_senders_server_wrong_senders, server_sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server_wrong_senders, host=server_sock[0], port=server_sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_allowed_senders_ipv6_wrong_senders(protocol_factory_allowed_senders_server_wrong_senders, server_sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_allowed_senders_server_wrong_senders, host='::1', port=server_sock[1])
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
async def udp_server_allowed_senders_ipv4(udp_protocol_factory_allowed_senders, server_sock) -> UDPServer:
    yield UDPServer(protocol_factory=udp_protocol_factory_allowed_senders, host=server_sock[0], port=server_sock[1])


@pytest.fixture
async def udp_server_allowed_senders_ipv4_started(udp_server_allowed_senders_ipv4) -> UDPServer:
    await udp_server_allowed_senders_ipv4.start()
    yield udp_server_allowed_senders_ipv4
    if udp_server_allowed_senders_ipv4.is_started():
        await udp_server_allowed_senders_ipv4.close()


@pytest.fixture
async def udp_server_allowed_senders_ipv6(udp_protocol_factory_allowed_senders, server_sock_ipv6) -> UDPServer:
    yield UDPServer(protocol_factory=udp_protocol_factory_allowed_senders, host=server_sock_ipv6[0], port=server_sock_ipv6[1])


@pytest.fixture
async def udp_server_allowed_senders_ipv6_started(udp_server_allowed_senders_ipv6) -> UDPServer:
    await udp_server_allowed_senders_ipv6.start()
    yield udp_server_allowed_senders_ipv6
    if udp_server_allowed_senders_ipv6.is_started():
        await udp_server_allowed_senders_ipv6.close()


@pytest.fixture
async def udp_server_allowed_senders_wrong_senders_ipv4(udp_protocol_factory_allowed_senders_wrong_senders, server_sock) -> UDPServer:
    server = UDPServer(protocol_factory=udp_protocol_factory_allowed_senders_wrong_senders, host=server_sock[0], port=server_sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def udp_server_allowed_senders_wrong_senders_ipv6(udp_protocol_factory_allowed_senders_wrong_senders, server_sock_ipv6) -> UDPServer:
    server = UDPServer(protocol_factory=udp_protocol_factory_allowed_senders_wrong_senders, host=server_sock_ipv6[0],
                       port=server_sock_ipv6[1])
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
async def sftp_protocol_factory_server_allowed_senders(buffered_file_storage_action, client_sock, client_sock_ipv6) -> SFTPOSAuthProtocolFactory:
    factory = SFTPOSAuthProtocolFactory(
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        allowed_senders=[IPNetwork(client_sock[0]), IPNetwork(client_sock_ipv6[0])]
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
async def sftp_server_allowed_senders_ip4(sftp_protocol_factory_server_allowed_senders, server_sock, tmp_path, ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_allowed_senders, host=server_sock[0], port=server_sock[1],
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_allowed_senders_ipv6(sftp_protocol_factory_server_allowed_senders, server_sock_ipv6, tmp_path, ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_allowed_senders, host=server_sock_ipv6[0], port=server_sock_ipv6[1],
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_not_allowed_senders_ip4(sftp_protocol_factory_server_not_allowed_senders, server_sock, tmp_path,
                                              ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_not_allowed_senders, host=server_sock[0],
                        port=server_sock[1], server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_not_allowed_senders_ipv6(sftp_protocol_factory_server_not_allowed_senders, server_sock_ipv6, tmp_path,
                                               ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_not_allowed_senders, host=server_sock_ipv6[0],
                        port=server_sock_ipv6[1], server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
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


@pytest.fixture
async def tcp_server_connections_expire(protocol_factory_server_connections_expire, server_sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_server_connections_expire, host=server_sock[0],
                       port=server_sock[1])
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_client_connections_expire(protocol_factory_client_connections_expire, server_sock, client_sock) -> TCPServer:
    yield TCPClient(protocol_factory=protocol_factory_client_connections_expire, host=server_sock[0],
                    port=server_sock[1], srcip=client_sock[0], srcport=0)


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_connections_expire.__name__, tcp_client_two_way.__name__)),
    lazy_fixture(
        (tcp_server_two_way_started.__name__, tcp_client_connections_expire.__name__))
])
def tcp_connections_expire_args(request):
    return request.param


@pytest.fixture
def server_expire_connections(tcp_connections_expire_args) -> BaseServer:
    return tcp_connections_expire_args[0]


@pytest.fixture
def client_expire_connections(tcp_connections_expire_args) -> BaseServer:
    return tcp_connections_expire_args[1]


@pytest.fixture
async def sftp_server_expire_connections(sftp_protocol_factory_server_expired_connections, server_sock, tmp_path,
                                         ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server_expired_connections, host=server_sock[0],
                        port=server_sock[1], server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_client_expire_connections(sftp_protocol_factory_client_expired_connections, server_sock, client_sock,
                                         sftp_username_password) -> SFTPServer:
    yield SFTPClient(protocol_factory=sftp_protocol_factory_client_expired_connections, host=server_sock[0],
                     port=server_sock[1], srcip=client_sock[0], srcport=0, username=sftp_username_password[0],
                     password=sftp_username_password[1])


@pytest.fixture(params=[
    lazy_fixture(
        (sftp_server_expire_connections.__name__, sftp_client.__name__)),
    lazy_fixture(
        (sftp_server_started.__name__, sftp_client_expire_connections.__name__))
])
def sftp_connections_expire_args(request):
    return request.param


@pytest.fixture
def sftp_server_for_expire_connections(sftp_connections_expire_args) -> BaseServer:
    return sftp_connections_expire_args[0]


@pytest.fixture
def sftp_client_for_expire_connections(sftp_connections_expire_args) -> BaseServer:
    return sftp_connections_expire_args[1]
