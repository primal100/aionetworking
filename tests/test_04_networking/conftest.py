from tests.test_03_requesters.conftest import *
import asyncio
import asyncssh
import datetime
from dataclasses import dataclass
import os
import pytest
import socket
from socket import AddressFamily, SocketKind

import logging
from aionetworking import (StreamServerProtocolFactory, StreamClientProtocolFactory, DatagramServerProtocolFactory,
                           DatagramClientProtocolFactory)
from aionetworking import Logger
from aionetworking.actions.file_storage import BufferedFileStorage
from aionetworking.formats.contrib.json import JSONObject
from aionetworking.networking import ReceiverAdaptor, SenderAdaptor
from aionetworking.networking import ConnectionsManager
from aionetworking.networking.connections_manager import clear_unique_names
from aionetworking.networking import (TCPServerConnection, TCPClientConnection,
                                      UDPServerConnection, UDPClientConnection)
from aionetworking.networking.sftp import SFTPClientProtocolFactory, SFTPFactory, SFTPClientProtocol
from aionetworking.networking.sftp_os_auth import SFTPOSAuthProtocolFactory, SFTPServerOSAuthProtocol
from aionetworking.networking import ServerSideSSL, ClientSideSSL
from aionetworking.networking.transports import DatagramTransportWrapper
from aionetworking.requesters.echo import EchoRequester
from aionetworking.networking.ssl_utils import generate_signed_key_cert_from_openssl_conf_file
from aionetworking.types.networking import SimpleNetworkConnectionType, AdaptorType
from aionetworking.utils import IPNetwork
from aionetworking.compatibility_tests import AsyncMock

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from pathlib import Path
from typing import Any, Callable, Dict, Type, Tuple, Union, Optional, List

from tests.mock import MockTCPTransport, MockDatagramTransport, MockAFInetSocket, MockAFUnixSocket, MockSFTPConn, \
    MockNamedPipeHandle


from unittest.mock import Mock


@pytest.fixture
def sftp_username_password() -> Tuple[str, str]:
    return 'testuser', 'abcd1234@'


@pytest.fixture
def patch_os_auth_ok() -> Callable:
    if os.name == 'posix':
        import pamela
        pamela.authenticate = Mock()
        return pamela.authenticate
    elif os.name == 'nt':
        import pywintypes
        import win32security
        win32security.LogonUser = Mock()
        return win32security.LogonUser


@pytest.fixture
def patch_os_auth_failure():
    if os.name == 'posix':
        import pamela
        pamela.authenticate = Mock(side_effect=pamela.PAMError())
        return pamela.authenticate
    elif os.name == 'nt':
        import pywintypes
        import win32security
        win32security.LogonUser = Mock(side_effect=pywintypes.error())
        return win32security.LogonUser


@pytest.fixture
def patch_os_call_args(sftp_username_password) -> Union[Tuple[str, str, str], Tuple[str, str, str, Any, Any]]:
    if os.name == 'posix':
        return sftp_username_password[0], sftp_username_password[1], 'sftplogin'
    elif os.name == 'nt':
        import pywintypes
        import win32con
        user, password = sftp_username_password
        return user, '.', password, win32con.LOGON32_LOGON_BATCH, win32con.LOGON32_PROVIDER_DEFAULT


@pytest.fixture
def critical_logging_only(caplog) -> None:
    caplog.set_level(logging.CRITICAL, logger="receiver.connection")


@pytest.fixture
def echo_decode_error_response_encoded(echo_exception_request_encoded) -> bytes:
    return b'{"error": "JSON was invalid"}'


@pytest.fixture
def requester(echo_requester, duplex_type) -> Optional[EchoRequester]:
    if duplex_type == 'twoway':
        return echo_requester


@pytest.fixture
async def requester_started(requester, sender_logger, endpoint) -> Optional[EchoRequester]:
    if endpoint == 'client' and requester:
        await requester.start(logger=sender_logger)
        yield requester
    else:
        yield None


@pytest.fixture
def preaction(recording_file_storage, endpoint) -> Optional[BufferedFileStorage]:
    if endpoint == 'server':
        return recording_file_storage


@pytest.fixture
async def preaction_started(preaction, receiver_logger) -> Optional[BufferedFileStorage]:
    if preaction:
        await preaction.start(logger=receiver_logger)
    yield preaction


@pytest.fixture
async def receiver_logger() -> Logger:
    logger = Logger(name='receiver', stats_interval=0.1, stats_fixed_start_time=False)
    yield logger


@pytest.fixture
def sender_logger() -> Logger:
    return Logger('sender')


@pytest.fixture
async def adaptor(context, endpoint, duplex_type, action, preaction, queue, requester, receiver_logger) -> AdaptorType:
    logger = receiver_logger.get_connection_logger(extra=context)
    if endpoint == 'server':
        adaptor = ReceiverAdaptor(JSONObject, context=context, action=action, preaction=preaction, send=queue.put_nowait, logger=logger)
    else:
        adaptor = SenderAdaptor(JSONObject, context=context, send=queue.put_nowait, requester=requester, logger=logger)
    yield adaptor
    await asyncio.wait_for(adaptor.close(), 3)


@pytest.fixture
async def file_containing_json_recording(tmpdir, buffer_codec, json_encoded_multi, timestamp) -> Path:
    obj1 = await buffer_codec.encode_obj(json_encoded_multi[0], system_timestamp=timestamp)
    await asyncio.sleep(1)
    obj2 = await buffer_codec.encode_obj(json_encoded_multi[1],
                                         system_timestamp=timestamp + datetime.timedelta(seconds=1,
                                                                                         microseconds=200000))
    p = Path(tmpdir.mkdir("recording") / "json.recording")
    p.write_bytes(obj1.encoded + obj2.encoded)
    return p


@pytest.fixture
def extra_server_inet(client_sock, server_sock) -> dict:
    return {'peername': client_sock, 'sockname': server_sock, 'socket': MockAFInetSocket()}


@pytest.fixture
def extra_client_inet(client_sock, server_sock) -> dict:
    return {'peername': server_sock, 'sockname': client_sock, 'socket': MockAFInetSocket()}


@pytest.fixture
def extra_server_pipe(pipe_path) -> Dict[str, Any]:
    if hasattr(socket, 'AF_UNIX'):
        return {'peername': '', 'socket': MockAFUnixSocket(), 'fd': 1, 'family': AddressFamily.AF_UNIX,
                'type': SocketKind.SOCK_STREAM, 'proto': 0, 'laddr': str(pipe_path), 'sockname': str(pipe_path)}
    return {'addr': str(pipe_path), 'pipe': MockNamedPipeHandle(12345)}


@pytest.fixture
def extra_client_pipe(pipe_path) -> Dict[str, Any]:
    if hasattr(socket, 'AF_UNIX'):
        return {'socket': MockAFUnixSocket(), 'fd': 1, 'family': AddressFamily.AF_UNIX, 'type': SocketKind.SOCK_STREAM,
                'proto': 0, 'raddr': str(pipe_path), 'sockname': '', 'peername': str(pipe_path)}
    return {'addr': str(pipe_path), 'pipe': MockNamedPipeHandle(12346)}


@pytest.fixture
def asyncssh_version():
    return asyncssh.__version__


@pytest.fixture
def extra_server_inet_sftp(client_sock, server_sock, asyncssh_version) -> dict:
    return {'peername': client_sock, 'sockname': server_sock, 'socket': MockAFInetSocket(),
            'username': 'testuser', 'client_version': f'SSH-2.0-AsyncSSH_{asyncssh_version}',
            'server_version': f'SSH-2.0-AsyncSSH_{asyncssh_version}',
            'send_cipher': 'chacha20-poly1305@openssh.com',
            'send_mac': 'chacha20-poly1305@openssh.com',
            'send_compression': 'zlib@openssh.com',
            'recv_cipher': 'chacha20-poly1305@openssh.com',
            'recv_mac': 'chacha20-poly1305@openssh.com',
            'recv_compression': 'zlib@openssh.com'}


@pytest.fixture
def extra_client_inet_sftp(client_sock, server_sock, asyncssh_version) -> dict:
    return {'peername': server_sock, 'sockname': client_sock, 'socket': MockAFInetSocket(), 'username': 'testuser',
            'client_version': f'SSH-2.0-AsyncSSH_{asyncssh_version}',
            'server_version': f'SSH-2.0-AsyncSSH_{asyncssh_version}',
            'send_cipher': 'chacha20-poly1305@openssh.com',
            'send_mac': 'chacha20-poly1305@openssh.com',
            'send_compression': 'zlib@openssh.com',
            'recv_cipher': 'chacha20-poly1305@openssh.com',
            'recv_mac': 'chacha20-poly1305@openssh.com',
            'recv_compression': 'zlib@openssh.com'}


@pytest.fixture
def mock_extra_server(connection_type, extra_server_inet, extra_server_pipe) -> Dict[str, Any]:
    if connection_type == 'pipe':
        return extra_server_pipe
    return extra_server_inet


@pytest.fixture
def mock_extra_client(connection_type, extra_client_inet, extra_client_pipe) -> Dict[str, Any]:
    if connection_type == 'pipe':
        return extra_client_pipe
    return extra_client_inet


@pytest.fixture
def mock_transport_class(connection_type) -> Type:
    classes = {
        'tcp': MockTCPTransport,
        'tcpssl': MockTCPTransport,
        'udp': MockDatagramTransport,
        'pipe': MockTCPTransport
    }
    return classes[connection_type]


@pytest.fixture
async def transport(mock_transport_class, connection_type, queue, peer, endpoint,
                    mock_extra_server, mock_extra_client) -> asyncio.Transport:
    extra = mock_extra_server if endpoint == 'server' else mock_extra_client
    transport = mock_transport_class(queue, extra=extra)
    if connection_type == 'udp':
        transport = DatagramTransportWrapper(transport, peer)
    yield transport
    if connection_type == 'udp' and not transport.is_closing:
        transport.close()


@pytest.fixture
def connection_cls(connection_type, endpoint) -> Type:
    connection_classes = {
        'server': {
            'tcp': TCPServerConnection,
            'tcpssl': TCPServerConnection,
            'udp': UDPServerConnection,
            'pipe': TCPServerConnection,
            'sftp': SFTPServerOSAuthProtocol
        },
        'client': {
            'tcp': TCPClientConnection,
            'tcpssl': TCPServerConnection,
            'udp': UDPClientConnection,
            'pipe': TCPClientConnection,
            'sftp': SFTPClientProtocol
        }
    }
    return connection_classes[endpoint][connection_type]


@pytest.fixture
def server_sock_as_string(connection_type, server_sock_str, pipe_path) -> str:
    if connection_type == 'pipe':
        return str(pipe_path)
    return server_sock_str


@pytest.fixture
def peer_prefix(connection_type) -> str:
    if connection_type == 'tcpssl':
        return 'tcp'
    if connection_type == 'pipe' and os.name == 'posix':
        return 'unix'
    return connection_type


@pytest.fixture
def parent_name(connection_type, endpoint, server_sock_as_string, peer_prefix) -> str:
    endpoint_type = endpoint.capitalize()
    return f"{peer_prefix.upper()} {endpoint_type} {server_sock_as_string}"


@pytest.fixture
def connection_kwargs_server(connection_type, tmpdir) -> Dict[str, Any]:
    return {}


@pytest.fixture
def connection_kwargs_client(connection_type, tmpdir) -> Dict[str, Any]:
    if connection_type == 'sftp':
        return {'base_path': Path(tmpdir) / 'sftp_sent'}
    return {}


@pytest.fixture
def connection_kwargs(connection_kwargs_server, connection_kwargs_client, endpoint) -> Dict[str, Any]:
    if endpoint == 'server':
        return connection_kwargs_server
    return connection_kwargs_client


@pytest.fixture
async def connection(connection_cls, connection_type, action_started, endpoint, preaction_started, parent_name,
                     peer_prefix, requester_started, server_sock_as_string, hostname_lookup, connection_kwargs,
                     receiver_logger) -> TCPServerConnection:
    conn = connection_cls(dataformat=JSONObject, action=action_started, preaction=preaction_started,
                          requester=requester_started, parent_name=parent_name, peer_prefix=peer_prefix,
                          hostname_lookup=hostname_lookup, logger=receiver_logger, timeout=5, **connection_kwargs)
    yield conn
    if connection_type == 'sftp':
        if not conn.is_closing():
            conn.close()
            await conn.wait_closed()
    else:
        if conn.transport and not conn.transport.is_closing():
            conn.transport.close()
    await asyncio.wait_for(conn.wait_closed(), 1)


@pytest.fixture(params=['ipv4', 'ipv6'])
def client_sock_ip_versions(request, client_sock, client_sock_ipv6) -> str:
    if request.param == 'ipv4':
        return client_sock[0]
    return client_sock_ipv6[0]


@pytest.fixture(params=['ipv4', 'ipv6', 'hostname'])
def allowed_sender_type(request) -> str:
    return request.param


@pytest.fixture
def allowed_sender(allowed_sender_type, client_sock, client_sock_ipv6, client_hostname) -> Tuple[str, str]:
    if allowed_sender_type == 'ipv4':
        return client_sock[0], client_sock[0]
    elif allowed_sender_type == 'ipv6':
        return client_sock_ipv6[0], client_sock_ipv6[0]
    return client_sock[0], client_hostname


@pytest.fixture
def incorrect_allowed_sender(allowed_sender_type, client_sock, client_sock_ipv6, client_hostname) -> Tuple[str, str]:
    if allowed_sender_type == 'ipv4':
        return '127.0.0.2', '127.0.0.2'
    elif allowed_sender_type == 'ipv6':
        return '::2', '::2'
    return '127.0.0.2', 'localhost2'


@pytest.fixture
def allowed_senders(allowed_sender_type, client_sock, client_sock_ipv6, client_hostname) -> Tuple[IPNetwork, IPNetwork]:
    if allowed_sender_type == 'hostname':
        return IPNetwork('10.10.10.10'), IPNetwork(client_hostname)
    return IPNetwork(client_sock[0]), IPNetwork(client_sock_ipv6[0])


@pytest.fixture
async def connection_allowed_senders(connection_cls, connection_type, action, endpoint, preaction, parent_name,
                                     peer_prefix,
                                     requester, server_sock_as_string, hostname_lookup, connection_kwargs, server_sock,
                                     allowed_senders) -> TCPServerConnection:
    if endpoint == 'client':
        action = None
    else:
        requester = None
    conn = connection_cls(dataformat=JSONObject, action=action, preaction=preaction, requester=requester,
                          parent_name=parent_name, peer_prefix=peer_prefix, hostname_lookup=hostname_lookup,
                          allowed_senders=allowed_senders, **connection_kwargs)
    yield conn
    if connection_type == 'sftp':
        if not conn.is_closing():
            conn.close()
            await conn.wait_closed()
    else:
        if conn.transport and not conn.transport.is_closing():
            conn.transport.close()
    await asyncio.wait_for(conn.wait_closed(), 1)


@pytest.fixture
async def second_connection(connection_cls, connection_type, action, endpoint, preaction, parent_name,
                            requester, server_sock_as_string, hostname_lookup) -> TCPServerConnection:
    conn = connection_cls(dataformat=JSONObject, action=action, preaction=preaction,
                          requester=requester, parent_name=parent_name,
                          peer_prefix=connection_type, hostname_lookup=hostname_lookup)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def connection_connected(connection, transport):
    connection.connection_made(transport)
    transport.set_protocol(connection)
    yield connection


@pytest.fixture
async def sftp_connection_connected(connection, endpoint, sftp_conn, sftp_factory):
    connection.connection_made(sftp_conn)
    if endpoint == 'client':
        await connection.set_sftp(sftp_factory)
    yield connection


@pytest.fixture
def hostname_lookup(connection_type) -> bool:
    return connection_type != 'pipe'


@pytest.fixture
async def protocol_factory_server(connection_type, action, recording_file_storage, hostname_lookup,
                                  connection_kwargs_server) -> StreamServerProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamServerProtocolFactory,
        'tcpssl': StreamServerProtocolFactory,
        'udp': DatagramServerProtocolFactory,
        'pipe': StreamServerProtocolFactory,
        'sftp': SFTPOSAuthProtocolFactory
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        preaction=recording_file_storage,
        action=action,
        dataformat=JSONObject,
        hostname_lookup=hostname_lookup,
        timeout=5,
        **connection_kwargs_server
    )
    yield factory


@pytest.fixture
async def protocol_factory_server_allowed_senders(connection_type, action, hostname_lookup, allowed_senders,
                                                  connection_kwargs_server) -> StreamServerProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamServerProtocolFactory,
        'udp': DatagramServerProtocolFactory,
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        action=action,
        dataformat=JSONObject,
        hostname_lookup=hostname_lookup,
        timeout=5,
        allowed_senders=allowed_senders,
        **connection_kwargs_server
    )
    yield factory


@pytest.fixture
async def protocol_factory_codec_kwargs(connection_type, action, hostname_lookup, receiver_logger,
                                        connection_kwargs_server, parent_name) -> StreamServerProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamServerProtocolFactory,
        'tcpssl': StreamServerProtocolFactory,
        'udp': DatagramServerProtocolFactory,
        'pipe': StreamServerProtocolFactory,
        'sftp': SFTPOSAuthProtocolFactory
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        action=action,
        dataformat=JSONObjectWithCodecKwargs,
        hostname_lookup=hostname_lookup,
        timeout=5,
        codec_config={'test_param': 'abc'},
        **connection_kwargs_server
    )
    await factory.start(logger=receiver_logger)
    if not factory.full_name:
        factory.set_name(parent_name, connection_type)
    yield factory
    factory.close_all_connections(None)
    await factory.close()


@pytest.fixture
async def protocol_factory_expire_connections(connection_type, action, hostname_lookup, connection_kwargs_server,
                                              receiver_logger, parent_name) -> StreamServerProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamServerProtocolFactory,
        'udp': DatagramServerProtocolFactory,
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        action=action,
        dataformat=JSONObject,
        hostname_lookup=hostname_lookup,
        timeout=5,
        expire_connections_after_inactive_minutes=1 / 60,
        expire_connections_check_interval_minutes=0.2 / 60,
        **connection_kwargs_server
    )
    await factory.start(logger=receiver_logger)
    if not factory.full_name:
        factory.set_name(parent_name, connection_type)
    yield factory
    factory.close_all_connections(None)
    await factory.close()


@pytest.fixture
async def protocol_factory_started(protocol_factory, receiver_logger, parent_name,
                                   connection_type) -> StreamServerProtocolFactory:
    await protocol_factory.start(logger=receiver_logger)
    if not protocol_factory.full_name:
        protocol_factory.set_name(parent_name, connection_type)
    yield protocol_factory
    await protocol_factory.close()


@pytest.fixture
async def protocol_factory_client(requester, connection_type, connection_kwargs_client,
                                  hostname_lookup) -> StreamClientProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamClientProtocolFactory,
        'tcpssl': StreamClientProtocolFactory,
        'udp': DatagramClientProtocolFactory,
        'pipe': StreamClientProtocolFactory,
        'sftp': SFTPClientProtocolFactory
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        dataformat=JSONObject,
        requester=requester,
        hostname_lookup=hostname_lookup,
        timeout=5,
        **connection_kwargs_client)
    yield factory


@pytest.fixture
async def protocol_factory_client_started(protocol_factory_client_started, parent_name,
                                          connection_type, receiver_logger) -> StreamClientProtocolFactory:
    await protocol_factory_client_started.start(logger=receiver_logger)
    if not protocol_factory_client_started.full_name:
        protocol_factory_client_started.set_name(parent_name, connection_type)
    yield protocol_factory_client_started
    await protocol_factory_client_started.close()


@pytest.fixture
def protocol_factory(protocol_factory_server, protocol_factory_client, endpoint):
    return protocol_factory_server if endpoint == 'server' else protocol_factory_client


@pytest.fixture
async def protocol_factory_started(protocol_factory, receiver_logger, parent_name, connection_type) -> StreamClientProtocolFactory:
    await protocol_factory.start(logger=receiver_logger)
    if not protocol_factory.full_name:
        protocol_factory.set_name(parent_name, connection_type)
    yield protocol_factory
    await protocol_factory.close()


@pytest.fixture
async def protocol_factory_server_connections_expire(echo_action) -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        hostname_lookup=True,
        expire_connections_after_inactive_minutes=1 / 60,
        expire_connections_check_interval_minutes=0.2 / 60
    )
    yield factory


@pytest.fixture
async def protocol_factory_client_connections_expire(echo_requester) -> StreamServerProtocolFactory:
    factory = StreamClientProtocolFactory(
        requester=echo_requester,
        dataformat=JSONObject,
        expire_connections_after_inactive_minutes=1 / 60,
        expire_connections_check_interval_minutes=0.2 / 60
    )
    yield factory


@pytest.fixture
async def udp_protocol_factory_server_connections_expire(echo_action) -> StreamServerProtocolFactory:
    factory = DatagramServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        hostname_lookup=True,
        expire_connections_after_inactive_minutes=1 / 60,
        expire_connections_check_interval_minutes=0.2 / 60
    )
    yield factory


@pytest.fixture
async def udp_protocol_factory_two_way_server(echo_action, buffered_file_storage_recording_action,
                                              ) -> DatagramServerProtocolFactory:
    factory = DatagramServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=echo_action,
        hostname_lookup=True,
        dataformat=JSONObject)
    yield factory



@pytest.fixture
async def sftp_protocol_factory_server(buffered_file_storage_action,
                                       buffered_file_storage_recording_action) -> SFTPOSAuthProtocolFactory:
    factory = SFTPOSAuthProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        hostname_lookup=True)
    yield factory


@pytest.fixture
async def sftp_protocol_factory_server_expired_connections(buffered_file_storage_action) -> SFTPOSAuthProtocolFactory:
    factory = SFTPOSAuthProtocolFactory(
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        hostname_lookup=True,
        expire_connections_after_inactive_minutes=1 / 60,
        expire_connections_check_interval_minutes=0.2 / 60
    )
    yield factory


@pytest.fixture
async def sftp_protocol_factory_client_expired_connections() -> SFTPClientProtocolFactory:
    factory = SFTPClientProtocolFactory(
        dataformat=JSONObject,
        hostname_lookup=True,
        expire_connections_after_inactive_minutes=1 / 60,
        expire_connections_check_interval_minutes=0.2 / 60
    )
    yield factory


@pytest.fixture
async def sftp_protocol_factory_client(tmpdir) -> SFTPClientProtocolFactory:
    factory = SFTPClientProtocolFactory(
        dataformat=JSONObject,
        hostname_lookup=True,
        base_path=Path(tmpdir) / 'sftp_sent',
    )
    yield factory


@pytest.fixture
def sftp_extra(endpoint, extra_server_inet_sftp, extra_client_inet_sftp) -> Dict[str, Any]:
    if endpoint == 'server':
        return extra_server_inet_sftp
    return extra_client_inet_sftp


@pytest.fixture
def sftp_conn(sftp_extra, connection) -> MockSFTPConn:
    yield MockSFTPConn(connection, extra=sftp_extra)


@pytest.fixture
def sftp_factory_server(sftp_one_way_conn_server, tmpdir) -> SFTPFactory:
    path = Path(tmpdir) / "sftp_received"
    yield SFTPFactory(sftp_one_way_conn_server, base_upload_dir=path)


@pytest.fixture
def sftp_one_way_conn_server(extra_server_inet_sftp, sftp_protocol_one_way_server) -> MockSFTPConn:
    yield MockSFTPConn(sftp_protocol_one_way_server, extra=extra_server_inet_sftp)


@pytest.fixture
def sftp_one_way_conn_client(extra_client_inet_sftp, sftp_protocol_one_way_client) -> MockSFTPConn:
    yield MockSFTPConn(sftp_protocol_one_way_client, extra=extra_client_inet_sftp)


@pytest.fixture
async def sftp_factory_client(sftp_one_way_conn_client) -> SFTPFactory:
    sftp_factory = asyncssh.SFTPClient(None, None, None)
    sftp_factory.realpath = AsyncMock(return_value='/')
    sftp_factory.put = AsyncMock()
    yield sftp_factory


@pytest.fixture
def sftp_factory(sftp_conn, tmpdir) -> SFTPFactory:
    path = Path(tmpdir) / "sftp_received"
    sftp_factory = SFTPFactory(sftp_conn, base_upload_dir=path)
    sftp_factory.realpath = AsyncMock(return_value='/')
    sftp_factory.put = AsyncMock()
    yield sftp_factory


@pytest.fixture
def sftp_context(endpoint, sftp_server_context, sftp_client_context) -> Dict[str, Any]:
    if endpoint == 'server':
        return sftp_server_context
    return sftp_client_context


@pytest.fixture
async def sftp_adaptor(action, preaction, endpoint, sftp_context, queue) -> ReceiverAdaptor:
    if endpoint == 'server':
        adaptor = ReceiverAdaptor(JSONObject, action=action, preaction=preaction, context=sftp_context)
    else:
        adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait, context=sftp_context)
    yield adaptor
    await adaptor.close()


@pytest.fixture
def test_networking_dir() -> Path:
    return Path(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture
def ssl_dir(test_networking_dir) -> Path:
    return test_networking_dir / "ssl"


@pytest.fixture
def ssl_server_dir(ssl_dir) -> Path:
    return ssl_dir / "server"


@pytest.fixture
def ssl_client_dir(ssl_dir) -> Path:
    return ssl_dir / "client"


@pytest.fixture
def ssl_server_cert(ssl_server_dir) -> Path:
    return ssl_server_dir / "certificate.pem"


@pytest.fixture
def ssl_server_key(ssl_server_dir) -> Path:
    return ssl_server_dir / "privkey.pem"


@pytest.fixture
def ssl_client_cert(ssl_client_dir) -> Path:
    return ssl_client_dir / "certificate.pem"


@pytest.fixture
def ssl_client_key(ssl_client_dir) -> Path:
    return ssl_client_dir / "privkey.pem"


@pytest.fixture
def peercert() -> Dict[str, Any]:
    return {'subject': ((('countryName', 'IE'),), (('stateOrProvinceName', 'Dublin'),), (('localityName', 'Dublin'),), (('organizationName', 'AIONetworking'),), (('organizationalUnitName', 'Client'),)), 'issuer': ((('countryName', 'IE'),), (('stateOrProvinceName', 'Dublin'),), (('localityName', 'Dublin'),), (('organizationName', 'AIONetworking'),), (('organizationalUnitName', 'Client'),)), 'version': 3, 'serialNumber': '0A7B7C8AF07F4E9A341F9695C06C2C1B70AED8C8', 'notBefore': 'Mar  8 11:13:58 2020 GMT', 'notAfter': 'Mar  6 11:13:58 2030 GMT'}


@pytest.fixture
def peercert_expires_soon(fixed_timestamp) -> Dict[str, Any]:
    return {'subject': ((('countryName', 'IE'),), (('stateOrProvinceName', 'Dublin'),), (('localityName', 'Dublin'),), (('organizationName', 'AIONetworking'),), (('organizationalUnitName', 'Client'),)), 'issuer': ((('countryName', 'IE'),), (('stateOrProvinceName', 'Dublin'),), (('localityName', 'Dublin'),), (('organizationName', 'AIONetworking'),), (('organizationalUnitName', 'Client'),)), 'version': 3, 'serialNumber': '0A7B7C8AF07F4E9A341F9695C06C2C1B70AED8C8', 'notBefore': 'Mar  8 11:13:58 2018 GMT', 'notAfter': 'Jan  2 11:13:58 2019 GMT'}


@pytest.fixture
def ssl_conf_file(ssl_dir) -> Path:
    return ssl_dir / 'ssl_localhost.cnf'


@pytest.fixture
def ssl_cert_key_short_validity_time(ssl_conf_file, tmpdir) -> Tuple[x509.Certificate, Path, rsa.RSAPrivateKey, Path]:
    return generate_signed_key_cert_from_openssl_conf_file(ssl_conf_file, tmpdir, validity=3)


@pytest.fixture
def short_validity_cert_actual_expiry_time(ssl_cert_key_short_validity_time) -> datetime.datetime:
    cert, cert_path, key, key_path = ssl_cert_key_short_validity_time
    return cert.not_valid_after


@pytest.fixture
async def server_side_ssl_short_validity(ssl_cert_key_short_validity_time, ssl_server_key, ssl_client_cert, ssl_client_dir):
    cert, cert_path, key, key_path = ssl_cert_key_short_validity_time
    server_side_ssl = ServerSideSSL(ssl=True, cert_required=False, cert=cert_path, key=key_path,
                                    warn_if_expires_before_days=7)
    yield server_side_ssl
    await server_side_ssl.close()


@pytest.fixture
async def server_side_ssl_long_validity(ssl_cert_key_short_validity_time, ssl_server_key, ssl_client_cert, ssl_client_dir):
    cert, cert_path, key, key_path = ssl_cert_key_short_validity_time
    server_side_ssl = ServerSideSSL(ssl=True, cert_required=False, cert=cert_path, key=key_path,
                                    warn_if_expires_before_days=1)
    yield server_side_ssl
    await server_side_ssl.close()


@pytest.fixture
def server_side_ssl(ssl_server_cert, ssl_server_key, ssl_client_cert, ssl_client_dir):
    return ServerSideSSL(ssl=True, cert_required=True, cert=ssl_server_cert, key=ssl_server_key,
                         cafile=ssl_client_cert, capath=ssl_client_dir)


@pytest.fixture
def client_side_ssl(ssl_client_cert, ssl_client_key, ssl_server_cert, ssl_server_dir):
    return ClientSideSSL(ssl=True, cert_required=True, cert=ssl_client_cert, key=ssl_client_key,
                         cafile=ssl_server_cert, capath=ssl_server_dir)


@pytest.fixture
def ssl_context(server_side_ssl, client_side_ssl, endpoint) -> Union[ServerSideSSL, ClientSideSSL]:
    if endpoint == 'server':
        return server_side_ssl
    return client_side_ssl


@pytest.fixture
def server_side_no_ssl():
    return ServerSideSSL(ssl=False)


@pytest.fixture
async def udp_protocol_factory_allowed_senders(echo_action, server_sock,
                                               server_sock_ipv6) -> DatagramServerProtocolFactory:
    factory = DatagramServerProtocolFactory(
        action=echo_action,
        dataformat=JSONObject,
        hostname_lookup=True,
        allowed_senders=[IPNetwork(server_sock[0]), IPNetwork(server_sock_ipv6[0])])
    await factory.start()
    yield factory
    await factory.close()


@pytest.fixture
async def protocol_factory_one_way_server_codec_kwargs(buffered_file_storage_action) -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        action=buffered_file_storage_action,
        dataformat=JSONObjectWithCodecKwargs,
        codec_config={'test_param': 'abc'}
    )
    await factory.start()
    yield factory
    await factory.close()


@pytest.fixture
async def queue() -> asyncio.Queue:
    yield asyncio.Queue()


@pytest.fixture
async def connections_manager() -> ConnectionsManager:
    from aionetworking.networking.connections_manager import connections_manager
    yield connections_manager
    connections_manager.clear()


@dataclass
class SimpleNetworkConnection:
    peer: str
    parent_name: str
    queue: asyncio.Queue

    async def wait_all_messages_processed(self) -> None: ...

    def encode_and_send_msg(self, msg_decoded: Any) -> None:
        self.queue.put_nowait(msg_decoded)


@pytest.fixture
def simple_network_connections(queue, client_sock_str) -> List[SimpleNetworkConnectionType]:
    return [SimpleNetworkConnection(client_sock_str, "TCP Server 127.0.0.1:8888", queue),
            SimpleNetworkConnection('127.0.0.1:4444', "TCP Server 127.0.0.1:8888", queue)]


@pytest.fixture
def simple_network_connection(simple_network_connections) -> SimpleNetworkConnectionType:
    return simple_network_connections[0]


@pytest.fixture
def reset_endpoint_names():
    clear_unique_names()
    yield
    clear_unique_names()

