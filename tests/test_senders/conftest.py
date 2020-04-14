from tests.test_receivers.conftest import *

import asyncio
import os
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
def actual_server_sock_expired_connections(server_expire_connections) -> Optional[Tuple[str, int]]:
    return getattr(server_expire_connections, 'actual_local_addr', (None, None))


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
def client_kwargs(connection_type, actual_server_sock, pipe_path, client_side_ssl, ssl_handshake_timeout, sftp_username_password) -> Dict[str, Any]:
    client_kwargs = {}
    if connection_type == 'tcpssl':
        client_kwargs.update({'ssl': client_side_ssl, 'ssl_handshake_timeout': ssl_handshake_timeout})
    elif connection_type == 'sftp':
        client_kwargs.update({'username': sftp_username_password[0], 'password': sftp_username_password[1]})
    if connection_type == 'pipe':
        client_kwargs.update({'path': pipe_path})
    else:
        client_kwargs.update({'host': actual_server_sock[0], 'port': actual_server_sock[1],
                              'srcip': actual_server_sock[0], 'srcport': 0})
    return client_kwargs


@pytest.fixture
def client_kwargs_fixed_port(connection_type, server_sock, pipe_path, client_side_ssl, ssl_handshake_timeout,
                             sftp_username_password) -> Dict[str, Any]:
    client_kwargs = {}
    if connection_type == 'tcpssl':
        client_kwargs.update({'ssl': client_side_ssl, 'ssl_handshake_timeout': ssl_handshake_timeout})
    elif connection_type == 'sftp':
        client_kwargs.update({'username': sftp_username_password[0], 'password': sftp_username_password[1]})
    if connection_type == 'pipe':
        client_kwargs.update({'path': pipe_path})
    else:
        client_kwargs.update({'host': server_sock[0], 'port': server_sock[1],
                              'srcip': server_sock[0], 'srcport': 0})
    return client_kwargs


@pytest.fixture
def tcp_client_allowed_sender(protocol_factory_client, actual_server_sock_allowed_senders, allowed_sender) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=allowed_sender[0], srcport=0)


@pytest.fixture
def tcp_client_incorrect_sender(protocol_factory_client, actual_server_sock_allowed_senders,
                                incorrect_allowed_sender) -> TCPClient:
    return TCPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=incorrect_allowed_sender[0], srcport=0)


@pytest.fixture
def client_cls(connection_type) -> Type:
    client_classes = {
        'tcp': TCPClient,
        'tcpssl': TCPClient,
        'udp': UDPClient,
        'pipe': PipeClient,
        'sftp': SFTPClient
    }
    client_cls = client_classes[connection_type]
    yield client_cls


@pytest.fixture
def udp_client(protocol_factory_client, actual_server_sock) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock[0],
                     port=actual_server_sock[1])


@pytest.fixture
def udp_client_allowed_sender(protocol_factory_client, actual_server_sock_allowed_senders, allowed_sender) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=allowed_sender[0])


@pytest.fixture
def udp_client_incorrect_sender(protocol_factory_client, actual_server_sock_allowed_senders,
                                incorrect_allowed_sender) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                     port=actual_server_sock_allowed_senders[1], srcip=incorrect_allowed_sender[0])


@pytest.fixture
def udp_client_connections_expire(protocol_factory_client, actual_server_sock_expired_connections,
                                  client_sock) -> UDPClient:
    return UDPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_expired_connections[0],
                     port=actual_server_sock_expired_connections[1], srcip=client_sock[0])


@pytest.fixture
async def client(connection_type, protocol_factory_client, client_cls, client_kwargs, patch_os_auth_ok) -> BaseNetworkClient:
    client = client_cls(protocol_factory=protocol_factory_client, **client_kwargs)
    yield client


@pytest.fixture
async def client_allowed_senders(connection_type, tcp_client_allowed_sender, udp_client_allowed_sender,
                                 sftp_client_allowed_sender, allowed_sender_type) -> BaseNetworkClient:
    if connection_type == 'udp' and allowed_sender_type == 'ipv6':
        if os.name == 'nt':
            pytest.skip()
    clients = {
        'tcp': tcp_client_allowed_sender,
        'udp': udp_client_allowed_sender,
        'sftp': sftp_client_allowed_sender
    }
    yield clients[connection_type]


@pytest.fixture
async def client_incorrect_sender(connection_type, allowed_sender_type, tcp_client_incorrect_sender,
                                  udp_client_incorrect_sender, sftp_client_incorrect_sender) -> BaseNetworkClient:
    if allowed_sender_type == 'ipv6':   # No spare localhost address in IPV6
        pytest.skip()
    clients = {
        'tcp': tcp_client_incorrect_sender,
        'udp': udp_client_incorrect_sender,
        'sftp': sftp_client_incorrect_sender
    }
    yield clients[connection_type]


@pytest.fixture
async def client_connections_expire(connection_type, tcp_client_connections_expire,
                                    udp_client_connections_expire) -> BaseNetworkClient:
    clients = {
        'tcp': tcp_client_connections_expire,
        'udp': udp_client_connections_expire,
    }
    yield clients[connection_type]


@pytest.fixture
async def client_fixed_port(connection_type, client_cls, protocol_factory_client, server_sock, client_sock, client_kwargs_fixed_port) -> BaseNetworkClient:
    client = client_cls(protocol_factory=protocol_factory_client, **client_kwargs_fixed_port)
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
def sftp_client_allowed_sender(protocol_factory_client, actual_server_sock_allowed_senders, client_sock,
                               sftp_username_password, patch_os_auth_ok, allowed_sender) -> SFTPClient:
    return SFTPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                      port=actual_server_sock_allowed_senders[1], srcip=allowed_sender[0], srcport=0,
                      username=sftp_username_password[0], password=sftp_username_password[1])


@pytest.fixture
def sftp_client_incorrect_sender(protocol_factory_client, actual_server_sock_allowed_senders, client_sock,
                                 sftp_username_password, patch_os_auth_ok, incorrect_allowed_sender) -> SFTPClient:
    return SFTPClient(protocol_factory=protocol_factory_client, host=actual_server_sock_allowed_senders[0],
                      port=actual_server_sock_allowed_senders[1], srcip=incorrect_allowed_sender[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])



@pytest.fixture
def sftp_client_ipv6(sftp_protocol_factory_client, server_sock_ipv6, client_sock_ipv6, sftp_username_password,
                     patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=server_sock_ipv6[0], port=server_sock_ipv6[1],
                      srcip=client_sock_ipv6[0], srcport=0, username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_exact_port(sftp_protocol_factory_client, server_sock, client_sock, sftp_username_password,
                           patch_os_auth_ok) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=server_sock[0], port=server_sock[1],
                      srcip=client_sock[0], srcport=client_sock[1], username=sftp_username_password[0],
                      password=sftp_username_password[1])


@pytest.fixture
def sftp_client_wrong_password(sftp_protocol_factory_client, actual_server_sock, client_sock, sftp_username_password,
                               patch_os_auth_failure) -> SFTPClient:
    return SFTPClient(protocol_factory=sftp_protocol_factory_client, host=actual_server_sock[0], port=actual_server_sock[1],
                      srcip=client_sock[0], srcport=0, username=sftp_username_password[0],
                      password='hello')


@pytest.fixture
async def tcp_client_connections_expire(protocol_factory_client_connections_expire,
                                        actual_server_sock_expired_connections, client_sock) -> TCPServer:
    yield TCPClient(protocol_factory=protocol_factory_client_connections_expire, host=actual_server_sock_expired_connections[0],
                    port=actual_server_sock_expired_connections[1], srcip=client_sock[0], srcport=0)
