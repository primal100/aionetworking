from tests.test_receivers.conftest import *

import asyncio
from dataclasses import replace

from aionetworking import TCPClient, UDPClient, PipeClient
from aionetworking.senders import BaseNetworkClient
from aionetworking.senders.sftp import SFTPClient


@pytest.fixture
def actual_server_sock(server_started) -> Optional[Tuple[str, int]]:
    return getattr(server_started, 'actual_local_addr', (None, None))


@pytest.fixture
def actual_server_sock_allowed_senders(server_allowed_senders) -> Optional[Tuple[str, int]]:
    return getattr(server_allowed_senders, 'actual_local_addr', (None, None))


@pytest.fixture
def actual_server_sock_ipv6(tcp_server_ipv6_started) -> Tuple[str, int]:
    return tcp_server_ipv6_started.actual_local_addr


@pytest.fixture
def actual_server_sock_ssl(tcp_server_ssl_started) -> Tuple[str, int]:
    return tcp_server_ssl_started.actual_local_addr


@pytest.fixture
def actual_client_sock(client_connected) -> Tuple[str, int]:
    return getattr(client_connected, 'actual_local_addr', (None, None))


@pytest.fixture
def actual_client_sock_ipv6(tcp_client_ipv6_started) -> Tuple[str, int]:
    return tcp_client_ipv6_started.actual_local_addr


@pytest.fixture
def actual_client_sock_ssl(tcp_client_ssl_started) -> Tuple[str, int]:
    return tcp_client_ssl_started.actual_local_addr


@pytest.fixture
def tcp_client(protocol_factory_client, actual_server_sock, client_sock) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=actual_server_sock[0], port=actual_server_sock[1],
                     srcip=client_sock[0], srcport=0)


@pytest.fixture
def tcp_client_ssl(protocol_factory_client, actual_server_sock, client_sock, client_side_ssl, ssl_handshake_timeout) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=actual_server_sock[0], port=actual_server_sock[1],
                     srcip=client_sock[0], srcport=0, ssl=client_side_ssl, ssl_handshake_timeout=ssl_handshake_timeout)


@pytest.fixture
def tcp_client_allowed_sender(protocol_factory_client, actual_server_sock_allowed_senders, allowed_sender) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=allowed_sender[0], srcport=0)


@pytest.fixture
def tcp_client_incorrect_sender(protocol_factory_client, actual_server_sock_allowed_senders, incorrect_allowed_sender) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=incorrect_allowed_sender[0], srcport=0)


@pytest.fixture
def tcp_client_ssl_fixed_port(protocol_factory_client, server_sock, client_sock, client_side_ssl, ssl_handshake_timeout) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=server_sock[0], port=server_sock[1],
                     srcip=client_sock[0], srcport=0, ssl=client_side_ssl, ssl_handshake_timeout=ssl_handshake_timeout)


@pytest.fixture
def tcp_client_fixed_port(protocol_factory_client, server_sock, client_sock) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=server_sock[0], port=server_sock[1],
                     srcip=client_sock[0], srcport=0)


@pytest.fixture
def udp_client(protocol_factory_client, actual_server_sock) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock[0],
                     port=actual_server_sock[1])


@pytest.fixture
def udp_client_allowed_sender(protocol_factory_client, actual_server_sock_allowed_senders, allowed_sender) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=allowed_sender[0])


@pytest.fixture
def udp_client_incorrect_sender(protocol_factory_client, actual_server_sock_allowed_senders, incorrect_allowed_sender) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=incorrect_allowed_sender[0])


@pytest.fixture
def udp_client_fixed_port(protocol_factory_client, server_sock) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=server_sock[0],
                     port=server_sock[1])


@pytest.fixture
def pipe_client(protocol_factory_client, pipe_path):
    return PipeClient(protocol_factory=protocol_factory_client, path=pipe_path)


@pytest.fixture
async def client(connection_type, tcp_client, tcp_client_ssl, udp_client, pipe_client, sftp_client) -> BaseNetworkClient:
    clients = {
        'tcp': tcp_client,
        'tcpssl': tcp_client_ssl,
        'udp': udp_client,
        'pipe': pipe_client,
        'sftp': sftp_client
    }
    client = clients[connection_type]
    yield client


@pytest.fixture
async def client_allowed_senders(connection_type, tcp_client_allowed_sender, udp_client_allowed_sender, sftp_client_allowed_sender, allowed_sender_type) -> BaseNetworkClient:
    if connection_type == 'udp' and allowed_sender_type == 'ipv6':
        if os.name == 'nt':
            pytest.skip()
    clients = {
        'tcp': tcp_client_allowed_sender,
        'tcpssl': tcp_client_ssl,
        'udp': udp_client_allowed_sender,
        'pipe': pipe_client,
        'sftp': sftp_client_allowed_sender
    }
    yield clients[connection_type]


@pytest.fixture
async def client_incorrect_sender(connection_type, allowed_sender_type, tcp_client_incorrect_sender, udp_client_incorrect_sender, sftp_client_incorrect_sender) -> BaseNetworkClient:
    if allowed_sender_type == 'ipv6':
        pytest.skip()
    clients = {
        'tcp': tcp_client_incorrect_sender,
        'tcpssl': tcp_client_ssl,
        'udp': udp_client_incorrect_sender,
        'pipe': pipe_client,
        'sftp': sftp_client_incorrect_sender
    }
    yield clients[connection_type]


@pytest.fixture
async def client_fixed_port(connection_type, tcp_client_fixed_port, tcp_client_ssl_fixed_port, udp_client_fixed_port,
                            pipe_client, sftp_client_fixed_port) -> BaseNetworkClient:
    clients = {
        'tcp': tcp_client_fixed_port,
        'tcpssl': tcp_client_ssl_fixed_port,
        'udp': udp_client_fixed_port,
        'pipe': pipe_client,
        'sftp': sftp_client_fixed_port
    }
    client = clients[connection_type]
    yield client


@pytest.fixture
async def client_connected(client, connections_manager):
    await asyncio.wait_for(client.connect(), 3)
    yield client
    if client.is_started():
        await asyncio.wait_for(client.close(), 3)


@pytest.fixture
def client_connection_started(client_connected):
    yield client_connected.conn


@pytest.fixture
def client_two(client) -> BaseNetworkClient:
    return replace(client)


@pytest.fixture
def tcp_client_ipv6(protocol_factory_two_way_client, actual_server_sock_ipv6, client_sock_ipv6) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=actual_server_sock_ipv6[0],
                     port=actual_server_sock_ipv6[1], srcip=client_sock_ipv6[0], srcport=0)


@pytest.fixture
def tcp_client_ssl_no_cadata(protocol_factory_two_way_client, server_sock, client_sock, client_side_ssl_no_cadata) -> TCPClient:
    client_side_ssl.check_hostname = False
    return TCPClient(protocol_factory=protocol_factory_two_way_client, host=server_sock[0], port=server_sock[1], srcip=client_sock[0],
                     srcport=0, ssl=client_side_ssl_no_cadata, ssl_handshake_timeout=60)


@pytest.fixture
def sftp_client(protocol_factory_client, actual_server_sock, client_sock, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=protocol_factory_client, host=actual_server_sock[0], port=actual_server_sock[1],
                      srcip=client_sock[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_allowed_sender(protocol_factory_client, actual_server_sock_allowed_senders, client_sock, sftp_username_password, patch_os_auth_ok, allowed_sender) -> SFTPClient:
    return SFTPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                      port=actual_server_sock_allowed_senders[1], srcip=allowed_sender[0], srcport=0,
                      username=sftp_username_password[0], password=sftp_username_password[1])


@pytest.fixture
def sftp_client_incorrect_sender(protocol_factory_client, actual_server_sock_allowed_senders, client_sock, sftp_username_password, patch_os_auth_ok, incorrect_allowed_sender) -> SFTPClient:
    return SFTPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                      port=actual_server_sock_allowed_senders[1], srcip=incorrect_allowed_sender[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_fixed_port(protocol_factory_client, server_sock, client_sock, sftp_username_password, patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=protocol_factory_client, host=server_sock[0], port=server_sock[1],
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
def sftp_client_wrong_password(sftp_protocol_factory_client, actual_server_sock, client_sock, sftp_username_password, patch_os_auth_failure) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=actual_server_sock[0], port=actual_server_sock[1],
                      srcip=client_sock[0], srcport=0, username=sftp_username_password[0],
                      password='abcdefgh')


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

