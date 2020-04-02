import asyncio
import asyncssh
import os
import socket

import logging
import datetime
from aionetworking import (StreamServerProtocolFactory, StreamClientProtocolFactory, DatagramServerProtocolFactory, \
                           DatagramClientProtocolFactory)
from aionetworking import context_cv
from aionetworking.networking import ReceiverAdaptor, SenderAdaptor
from aionetworking.networking import ConnectionsManager
from aionetworking.networking.connections_manager import clear_unique_names
from aionetworking.networking import (TCPServerConnection, TCPClientConnection,
                                      UDPServerConnection, UDPClientConnection)
from aionetworking.networking.sftp import SFTPClientProtocolFactory, SFTPFactory, SFTPClientProtocol
from aionetworking.networking.sftp_os_auth import SFTPOSAuthProtocolFactory, SFTPServerOSAuthProtocol
from aionetworking.networking import ServerSideSSL, ClientSideSSL
from aionetworking.networking.transports import DatagramTransportWrapper
from aionetworking.types.networking import SimpleNetworkConnectionType, AdaptorType
from aionetworking.utils import IPNetwork
from aionetworking.compatibility_tests import AsyncMock

from typing import Callable, Union

from tests.mock import MockTCPTransport, MockDatagramTransport, MockAFInetSocket, MockAFUnixSocket, MockSFTPConn, MockNamedPipeHandle

from tests.test_requesters.conftest import *

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
def preaction(recording_file_storage, endpoint) -> Optional[BufferedFileStorage]:
    if endpoint == 'server':
        return recording_file_storage


@pytest.fixture
async def adaptor(context, endpoint, duplex_type, action, preaction, queue, requester) -> AdaptorType:
    context_cv.set(context)
    if endpoint == 'server':
        adaptor = ReceiverAdaptor(JSONObject, action=action, preaction=preaction, send=queue.put_nowait)
    else:
        adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait, requester=requester)
    yield adaptor
    await adaptor.close()


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
        return {'peername': str(pipe_path), 'socket': MockAFUnixSocket()}
    return {'addr': str(pipe_path), 'pipe': MockNamedPipeHandle(12345)}


@pytest.fixture
def extra_client_pipe(pipe_path) -> Dict[str, Any]:
    if hasattr(socket, 'AF_UNIX'):
        return {'peername': str(pipe_path), 'socket': MockAFUnixSocket()}
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
            'udp': UDPServerConnection,
            'pipe': TCPServerConnection
        },
        'client': {
            'tcp': TCPClientConnection,
            'udp': UDPClientConnection,
            'pipe': TCPClientConnection
        }
    }
    return connection_classes[endpoint][connection_type]


@pytest.fixture
def server_sock_as_string(connection_type, server_sock_str, pipe_path) -> str:
    if connection_type == 'pipe':
        return str(pipe_path)
    return server_sock_str


@pytest.fixture
def parent_name(connection_type, endpoint, server_sock_as_string) -> str:
    endpoint_type = endpoint.capitalize()
    return f"{connection_type.upper()} {endpoint_type} {server_sock_as_string}"


@pytest.fixture
async def connection(connection_cls, connection_type, action, endpoint, preaction, parent_name,
                     requester, server_sock_as_string, hostname_lookup) -> TCPServerConnection:
    if endpoint == 'client':
        action = None
    else:
        requester = None
    conn = connection_cls(dataformat=JSONObject, action=action, preaction=preaction,
                          requester=requester, parent_name=parent_name,
                          peer_prefix=connection_type, hostname_lookup=hostname_lookup)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


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
def hostname_lookup(connection_type) -> bool:
    return connection_type != 'pipe'


@pytest.fixture
async def protocol_factory_server(connection_type, action, recording_file_storage, hostname_lookup) -> StreamServerProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamServerProtocolFactory,
        'udp': DatagramServerProtocolFactory,
        'pipe': StreamServerProtocolFactory,
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        preaction=recording_file_storage,
        action=action,
        dataformat=JSONObject,
        hostname_lookup=hostname_lookup
    )
    yield factory


@pytest.fixture
async def protocol_factory_started(protocol_factory, parent_name, connection_type) -> StreamServerProtocolFactory:
    await protocol_factory.start()
    if not protocol_factory.full_name:
        protocol_factory.set_name(parent_name, connection_type)
    yield protocol_factory
    await protocol_factory.close()


@pytest.fixture
async def protocol_factory_client(requester, connection_type) -> StreamClientProtocolFactory:
    protocol_factory_classes = {
        'tcp': StreamClientProtocolFactory,
        'udp': DatagramClientProtocolFactory,
        'pipe': StreamClientProtocolFactory,
    }
    factory_cls = protocol_factory_classes[connection_type]
    factory = factory_cls(
        dataformat=JSONObject,
        requester=requester,
        hostname_lookup=True)
    yield factory


@pytest.fixture
async def protocol_factory_client_started(protocol_factory_client_started, parent_name, connection_type) -> StreamClientProtocolFactory:
    await protocol_factory_client_started.start()
    if not protocol_factory_client_started.full_name:
        protocol_factory_client_started.set_name(parent_name, connection_type)
    yield protocol_factory_client_started
    await protocol_factory_client_started.close()


@pytest.fixture
def protocol_factory(protocol_factory_server, protocol_factory_client, endpoint):
    return protocol_factory_server if endpoint == 'server' else protocol_factory_client


@pytest.fixture
async def protocol_factory_started(protocol_factory, parent_name, connection_type) -> StreamClientProtocolFactory:
    await protocol_factory.start()
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
async def protocol_factory_server_connections_expire_started(protocol_factory_server_connections_expire,
                                                             initial_server_context,
                                                             server_sock_str) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    await protocol_factory_server_connections_expire.start()
    if not protocol_factory_server_connections_expire.full_name:
        protocol_factory_server_connections_expire.set_name(f'TCP Server {server_sock_str}', 'tcp')
    yield protocol_factory_server_connections_expire
    await protocol_factory_server_connections_expire.close()


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
async def udp_protocol_factory_server_connections_expire_started(udp_protocol_factory_server_connections_expire,
                                                                 initial_server_context,
                                                                 server_sock_str) -> DatagramServerProtocolFactory:
    context_cv.set(initial_server_context)
    await udp_protocol_factory_server_connections_expire.start()
    if not udp_protocol_factory_server_connections_expire.full_name:
        udp_protocol_factory_server_connections_expire.set_name(f'UDP Server {server_sock_str}', 'udp')
    yield udp_protocol_factory_server_connections_expire
    await udp_protocol_factory_server_connections_expire.close()


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
async def udp_protocol_factory_two_way_server_started(udp_protocol_factory_two_way_server, server_sock_str,
                                                      udp_initial_server_context) -> DatagramServerProtocolFactory:
    context_cv.set(udp_initial_server_context)
    await udp_protocol_factory_two_way_server.start()
    if not udp_protocol_factory_two_way_server.full_name:
        udp_protocol_factory_two_way_server.set_name(f'UDP Server {server_sock_str}', 'udp')
    yield udp_protocol_factory_two_way_server
    if udp_protocol_factory_two_way_server.transport and not udp_protocol_factory_two_way_server.transport.is_closing():
        await udp_protocol_factory_two_way_server.close()


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
async def sftp_protocol_factory_server_started(sftp_protocol_factory_server, server_sock_str,
                                               sftp_initial_server_context) -> SFTPOSAuthProtocolFactory:
    context_cv.set(sftp_initial_server_context)
    await sftp_protocol_factory_server.start()
    if not sftp_protocol_factory_server.full_name:
        sftp_protocol_factory_server.set_name(f'SFTP Server {server_sock_str}', 'sftp')
    yield sftp_protocol_factory_server
    await sftp_protocol_factory_server.close()


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
async def sftp_protocol_factory_server_expired_connections_started(sftp_protocol_factory_server_expired_connections,
                                                                   server_sock_str,
                                                                   sftp_initial_server_context) -> SFTPOSAuthProtocolFactory:
    context_cv.set(sftp_initial_server_context)
    await sftp_protocol_factory_server_expired_connections.start()
    if not sftp_protocol_factory_server_expired_connections.full_name:
        sftp_protocol_factory_server_expired_connections.set_name(f'SFTP Server {server_sock_str}', 'sftp')
    yield sftp_protocol_factory_server_expired_connections
    await sftp_protocol_factory_server_expired_connections.close()


@pytest.fixture
async def sftp_protocol_factory_client(tmpdir) -> SFTPClientProtocolFactory:
    factory = SFTPClientProtocolFactory(
        dataformat=JSONObject,
        hostname_lookup=True,
        base_path=Path(tmpdir) / 'sftp_sent',
    )
    yield factory


@pytest.fixture
async def sftp_protocol_factory_client_started(sftp_initial_client_context, sftp_protocol_factory_client, tmpdir,
                                               server_sock_str) -> SFTPClientProtocolFactory:
    context_cv.set(sftp_initial_client_context)
    await sftp_protocol_factory_client.start()
    if not sftp_protocol_factory_client.full_name:
        sftp_protocol_factory_client.set_name(f'SFTP Client {server_sock_str}', 'sftp')
    yield sftp_protocol_factory_client
    await sftp_protocol_factory_client.close()


@pytest.fixture
async def sftp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                       sftp_initial_server_context, server_sock_str) -> SFTPServerOSAuthProtocol:
    context_cv.set(sftp_initial_server_context)
    protocol = SFTPServerOSAuthProtocol(dataformat=JSONObject, action=buffered_file_storage_action,
                                        parent_name=f"SFTP Server {server_sock_str}", peer_prefix='sftp',
                                        preaction=buffered_file_storage_recording_action, hostname_lookup=True)
    yield protocol
    if not protocol.is_closing():
        protocol.close()
        await protocol.wait_closed()


@pytest.fixture
async def sftp_protocol_one_way_client(sftp_initial_client_context, tmpdir, server_sock_str) -> SFTPClientProtocol:
    context_cv.set(sftp_initial_client_context)
    protocol = SFTPClientProtocol(dataformat=JSONObject, peer_prefix='sftp',
                                  parent_name=f"SFTP Client {server_sock_str}",
                                  base_path=Path(tmpdir) / 'sftp_sent', hostname_lookup=True)
    yield protocol
    if not protocol.is_closing():
        protocol.close()
        await protocol.wait_closed()


@pytest.fixture
def sftp_conn_server(request, extra_server_inet_sftp, sftp_protocol) -> MockSFTPConn:
    sftp_protocol = request.getfixturevalue(sftp_protocol.name)
    yield MockSFTPConn(sftp_protocol, extra=extra_server_inet_sftp)


@pytest.fixture
def server_sftp_conn(extra_server_inet_sftp, sftp_protocol_one_way_server) -> MockSFTPConn:
    yield MockSFTPConn(sftp_protocol_one_way_server, extra=extra_server_inet_sftp)


@pytest.fixture
def sftp_conn_client(request, extra_client_inet_sftp, sftp_protocol) -> MockSFTPConn:
    sftp_protocol = request.getfixturevalue(sftp_protocol.name)
    yield MockSFTPConn(sftp_protocol, extra=extra_client_inet_sftp)


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
def sftp_factory(request, sftp_conn, tmpdir) -> SFTPFactory:
    sftp_conn = request.getfixturevalue(sftp_conn.name)
    path = Path(tmpdir) / "sftp_received"
    yield SFTPFactory(sftp_conn, base_upload_dir=path)


@pytest.fixture
async def sftp_one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action,
                                        sftp_server_context) -> ReceiverAdaptor:
    context_cv.set(sftp_server_context)
    adaptor = ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                              preaction=buffered_file_storage_recording_action)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def sftp_one_way_sender_adaptor(sftp_client_context, queue) -> SenderAdaptor:
    context_cv.set(sftp_client_context)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
def sftp_protocol_factory(sftp_connection_args) -> Union[SFTPOSAuthProtocolFactory, SFTPClientProtocolFactory]:
    return sftp_connection_args[0]


@pytest.fixture
def sftp_protocol(sftp_connection_args) -> Union[SFTPServerOSAuthProtocol, SFTPClientProtocol]:
    return sftp_connection_args[1]


@pytest.fixture
def sftp_conn(sftp_connection_args) -> MockSFTPConn:
    return sftp_connection_args[2]


@pytest.fixture
def sftp_adaptor(sftp_connection_args) -> Union[SenderAdaptor, ReceiverAdaptor]:
    return sftp_connection_args[3]


@pytest.fixture
def sftp_peer(sftp_connection_args) -> Tuple[str, int]:
    return sftp_connection_args[4]


@pytest.fixture
def sftp_connection_is_stored(sftp_connection_args) -> bool:
    return sftp_connection_args[5]


@pytest.fixture
def current_dir() -> Path:
    return Path(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture
def ssl_dir(current_dir) -> Path:
    return current_dir / "ssl"


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
def server_side_ssl(ssl_server_cert, ssl_server_key, ssl_client_cert, ssl_client_dir):
    return ServerSideSSL(ssl=True, cert_required=True, check_hostname=True, cert=ssl_server_cert, key=ssl_server_key,
                         cafile=ssl_client_cert, capath=ssl_client_dir)


@pytest.fixture
def client_side_ssl(ssl_server_cert, ssl_server_key, ssl_client_cert, ssl_client_dir):
    return ServerSideSSL(ssl=True, cert_required=True, check_hostname=True, cert=ssl_server_cert, key=ssl_server_key,
                         cafile=ssl_client_cert, capath=ssl_client_dir)


@pytest.fixture
def ssl_context(server_side_ssl, client_side_ssl, endpoint) -> Union[ServerSideSSL, ClientSideSSL]:
    if endpoint == 'server':
        return server_side_ssl
    return client_side_ssl


"""@pytest.fixture
def client_side_ssl_no_cadata(ssl_client_cert, ssl_client_key, ssl_server_cert, ssl_server_dir) -> ClientSideSSL:
    return ClientSideSSL(ssl=True, cert_required=True, check_hostname=True, cert=ssl_client_cert, key=ssl_client_key,
                         cafile=ssl_server_cert, capath=ssl_server_dir)"""


@pytest.fixture
def server_side_no_ssl():
    return ServerSideSSL(ssl=False)


@pytest.fixture
async def tcp_protocol_two_way_server_allowed_senders(echo_action, initial_server_context, server_sock,
                                                      server_sock_ipv6,
                                                      server_sock_str, client_hostname) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=echo_action, hostname_lookup=True,
                               allowed_senders=[IPNetwork(server_sock[0]), IPNetwork(server_sock_ipv6[0])],
                               parent_name=f"TCP Server {server_sock_str}", peer_prefix='tcp')
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_server_allowed_senders_hostname(echo_action, initial_server_context,
                                                               server_sock_str, client_hostname) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=echo_action, hostname_lookup=True,
                               allowed_senders=[IPNetwork(client_hostname)],
                               parent_name=f"TCP Server {server_sock_str}", peer_prefix='tcp')
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


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
