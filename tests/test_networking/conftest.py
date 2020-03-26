from pytest_lazyfixture import lazy_fixture, is_lazy_fixture
import asyncssh
import os

import logging
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
from aionetworking.types.networking import SimpleNetworkConnectionType, AFINETContext, AFUNIXContext, NamedPipeContext, SFTPContext
from aionetworking.utils import IPNetwork
from aionetworking.compatibility_tests import AsyncMock

from typing import Union

from tests.mock import MockTCPTransport, MockDatagramTransport, MockAFInetSocket, MockAFUnixSocket, MockSFTPConn

from tests.test_requesters.conftest import *

from unittest.mock import Mock


@pytest.fixture
def patch_datetime_now(monkeypatch):
    FAKE_TIME = datetime.datetime(2019, 1, 1, 1, 1, 1)

    class FreezeDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return FAKE_TIME

    monkeypatch.setattr(datetime, 'datetime', FreezeDatetime)


@pytest.fixture
def sftp_username_password():
    return 'testuser', 'abcd1234@'


@pytest.fixture
def patch_os_auth_ok():
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
def patch_os_call_args(sftp_username_password):
    if os.name == 'posix':
        return sftp_username_password[0], sftp_username_password[1], 'sftplogin'
    elif os.name == 'nt':
        import pywintypes
        import win32con
        user, password = sftp_username_password
        return (user, '.', password, win32con.LOGON32_LOGON_BATCH, win32con.LOGON32_PROVIDER_DEFAULT)


@pytest.fixture
def critical_logging_only(caplog):
    caplog.set_level(logging.CRITICAL, logger="receiver.connection")


@pytest.fixture
def initial_server_context(server_sock_str) -> Dict[str, Any]:
    return {}


@pytest.fixture
def initial_client_context() -> Dict[str, Any]:
    return {}


@pytest.fixture
def udp_initial_server_context(server_sock_str) -> Dict[str, Any]:
    return {}


@pytest.fixture
def udp_initial_client_context() -> Dict[str, Any]:
    return {}


@pytest.fixture
def sftp_initial_server_context(server_sock_str) -> Dict[str, Any]:
    return {}


@pytest.fixture
def sftp_initial_client_context() -> Dict[str, Any]:
    return {}


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


@pytest.fixture
def json_client_codec(tcp_client_context) -> JSONCodec:
    return JSONCodec(JSONObject, context=tcp_client_context)


@pytest.fixture
def echo_decode_error_response_encoded(echo_exception_request_encoded) -> bytes:
    return b'{"error": "JSON was invalid"}'


@pytest.fixture
def echo_recording_data(client_sock) -> List:
    return [recorded_packet(sent_by_server=False, timestamp=datetime.datetime(2019, 1, 1, 1, 1), sender=client_sock[0],
                            data=b'{"id": 1, "method": "echo"}')]


@pytest.fixture
async def one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action,
                                   tcp_server_context) -> ReceiverAdaptor:
    context_cv.set(tcp_server_context)
    adaptor = ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                              preaction=buffered_file_storage_recording_action)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def one_way_sender_adaptor(tcp_client_context,queue) -> SenderAdaptor:
    context_cv.set(tcp_client_context)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def two_way_receiver_adaptor(echo_action, buffered_file_storage_recording_action, tcp_server_context, queue) -> ReceiverAdaptor:
    context_cv.set(tcp_server_context)
    adaptor = ReceiverAdaptor(JSONObject, action=echo_action, preaction=buffered_file_storage_recording_action,
                              send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def two_way_sender_adaptor(echo_requester, tcp_client_context, queue) -> SenderAdaptor:
    context_cv.set(tcp_client_context)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait, requester=echo_requester)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action, tcp_server_context) -> ReceiverAdaptor:
    context_cv.set(tcp_server_context)
    adaptor = ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                              preaction=buffered_file_storage_recording_action)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def one_way_sender_adaptor(tcp_client_context, queue) -> SenderAdaptor:
    context_cv.set(tcp_client_context)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def udp_two_way_receiver_adaptor(echo_action, buffered_file_storage_recording_action, udp_server_context,
                                       queue) -> ReceiverAdaptor:
    context_cv.set(udp_server_context)
    adaptor = ReceiverAdaptor(JSONObject, action=echo_action, preaction=buffered_file_storage_recording_action,
                              send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def udp_two_way_sender_adaptor(echo_requester, udp_client_context, queue) -> SenderAdaptor:
    context_cv.set(udp_client_context)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait, requester=echo_requester)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def udp_one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action, udp_server_context) -> ReceiverAdaptor:
    context_cv.set(udp_server_context)
    adaptor = ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                              preaction=buffered_file_storage_recording_action)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def udp_one_way_sender_adaptor(udp_client_context, queue) -> SenderAdaptor:
    context_cv.set(udp_client_context)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def file_containing_json_recording(tmpdir, buffer_codec, json_encoded_multi, timestamp) -> Path:
    obj1 = await buffer_codec.encode_obj(json_encoded_multi[0], system_timestamp=timestamp)
    await asyncio.sleep(1)
    obj2 = await buffer_codec.encode_obj(json_encoded_multi[1],
                                   system_timestamp=timestamp + datetime.timedelta(seconds=1, microseconds=200000))
    p = Path(tmpdir.mkdir("recording") / "json.recording")
    p.write_bytes(obj1.encoded + obj2.encoded)
    return p


@pytest.fixture
def extra_inet(client_sock, server_sock) -> dict:
    return {'peername': client_sock, 'sockname': server_sock, 'socket': MockAFInetSocket()}


@pytest.fixture
def extra_client_inet(client_sock, server_sock) -> dict:
    return {'peername': server_sock, 'sockname': client_sock, 'socket': MockAFInetSocket()}


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
def extra_unix(client_sock, server_sock) -> dict:
    return {'peername': client_sock, 'sockname': server_sock, 'socket': MockAFUnixSocket()}


@pytest.fixture
def extra_client_unix(client_sock, server_sock) -> dict:
    return {'peername': server_sock, 'sockname': client_sock, 'socket': MockAFUnixSocket()}


@pytest.fixture
async def tcp_transport(queue, extra_inet) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra_inet)


@pytest.fixture
async def tcp_transport_client(queue, extra_client_inet) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra_client_inet)


@pytest.fixture
async def unix_transport(queue, extra_unix) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra_unix)


@pytest.fixture
async def unix_transport_client(queue, extra_client_unix) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra_client_unix)


@pytest.fixture
async def udp_transport_server(queue, extra_inet) -> MockDatagramTransport:
    transport = MockDatagramTransport(queue, extra=extra_inet)
    yield transport
    if not transport.is_closing():
        transport.close()


@pytest.fixture
async def udp_transport_client(queue, extra_client_inet) -> MockDatagramTransport:
    yield MockDatagramTransport(queue, extra=extra_client_inet)


@pytest.fixture
async def udp_transport_wrapper_server(udp_transport_server, queue, client_sock) -> DatagramTransportWrapper:
    yield DatagramTransportWrapper(udp_transport_server, client_sock)


@pytest.fixture
async def udp_transport_wrapper_client(udp_transport_client, server_sock) -> DatagramTransportWrapper:
    yield DatagramTransportWrapper(udp_transport_client, server_sock)


@pytest.fixture
async def protocol_factory_one_way_server(buffered_file_storage_action,
                                          buffered_file_storage_recording_action) -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        hostname_lookup=True
    )
    yield factory


@pytest.fixture
async def protocol_factory_one_way_server_pipe(buffered_file_storage_action,
                                          buffered_file_storage_recording_action) -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject
    )
    yield factory


@pytest.fixture
async def protocol_factory_one_way_server_started(protocol_factory_one_way_server, initial_server_context,
                                                  server_sock_str) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    await protocol_factory_one_way_server.start()
    if not protocol_factory_one_way_server.full_name:
        protocol_factory_one_way_server.set_name(f'TCP Server {server_sock_str}', 'tcp')
    yield protocol_factory_one_way_server
    await protocol_factory_one_way_server.close()


@pytest.fixture
async def protocol_factory_one_way_server_pipe_started(protocol_factory_one_way_server_pipe, initial_server_context,
                                                       pipe_path) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    await protocol_factory_one_way_server_pipe.start()
    if not protocol_factory_one_way_server_pipe.full_name:
        protocol_factory_one_way_server_pipe.set_name(f'Pipe Server {pipe_path}', 'pipe')
    yield protocol_factory_one_way_server_pipe
    await protocol_factory_one_way_server_pipe.close()


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
async def protocol_factory_one_way_server_started(protocol_factory_one_way_server, initial_server_context,
                                                  server_sock_str) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    await protocol_factory_one_way_server.start()
    if not protocol_factory_one_way_server.full_name:
        protocol_factory_one_way_server.set_name(f'TCP Server {server_sock_str}', 'tcp')
    yield protocol_factory_one_way_server
    await protocol_factory_one_way_server.close()


@pytest.fixture
async def protocol_factory_two_way_server(echo_action, buffered_file_storage_recording_action,
                                          initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=echo_action,
        dataformat=JSONObject,
        hostname_lookup=True
    )
    yield factory


@pytest.fixture
async def protocol_factory_two_way_server_pipe(echo_action, buffered_file_storage_recording_action,
                                               initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=echo_action,
        dataformat=JSONObject,
    )
    yield factory


@pytest.fixture
async def protocol_factory_two_way_server_started(protocol_factory_two_way_server, server_sock_str,
                                                  initial_server_context) -> StreamServerProtocolFactory:
        context_cv.set(initial_server_context)
        await protocol_factory_two_way_server.start()
        if not protocol_factory_two_way_server.full_name:
            protocol_factory_two_way_server.set_name(f'TCP Server {server_sock_str}', 'tcp')
        yield protocol_factory_two_way_server
        await protocol_factory_two_way_server.close()


@pytest.fixture
async def protocol_factory_two_way_server_pipe_started(protocol_factory_two_way_server_pipe,
                                                       initial_server_context, pipe_path) -> StreamServerProtocolFactory:
        context_cv.set(initial_server_context)
        await protocol_factory_two_way_server_pipe.start()
        if not protocol_factory_two_way_server_pipe.full_name:
            protocol_factory_two_way_server_pipe.set_name(f'Pipe Server {pipe_path}', 'pipe')
        yield protocol_factory_two_way_server_pipe
        await protocol_factory_two_way_server_pipe.close()


@pytest.fixture
async def protocol_factory_one_way_client() -> StreamClientProtocolFactory:
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject,
        hostname_lookup=True)
    yield factory


@pytest.fixture
async def protocol_factory_one_way_client_started(protocol_factory_one_way_client, initial_client_context, server_sock_str) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    await protocol_factory_one_way_client.start()
    if not protocol_factory_one_way_client.full_name:
        protocol_factory_one_way_client.set_name(f'TCP Client {server_sock_str}', 'tcp')
    yield protocol_factory_one_way_client
    await protocol_factory_one_way_client.close()


@pytest.fixture
async def protocol_factory_two_way_client(echo_requester) -> StreamClientProtocolFactory:
    factory = StreamClientProtocolFactory(
        requester=echo_requester,
        dataformat=JSONObject,
        hostname_lookup=True)
    yield factory


@pytest.fixture
async def protocol_factory_two_way_client_started(protocol_factory_two_way_client, initial_client_context, server_sock_str) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    await protocol_factory_two_way_client.start()
    if not protocol_factory_two_way_client.full_name:
        protocol_factory_two_way_client.set_name(f'TCP Client {server_sock_str}', 'tcp')
    yield protocol_factory_two_way_client
    await protocol_factory_two_way_client.close()


@pytest.fixture
async def protocol_factory_one_way_client_pipe() -> StreamClientProtocolFactory:
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject)
    yield factory


@pytest.fixture
async def protocol_factory_one_way_client_pipe_started(protocol_factory_one_way_client_pipe, initial_client_context, pipe_path) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    await protocol_factory_one_way_client_pipe.start()
    if not protocol_factory_one_way_client_pipe.full_name:
        protocol_factory_one_way_client_pipe.set_name(f'Pipe Client {pipe_path}', 'pipe')
    yield protocol_factory_one_way_client_pipe
    await protocol_factory_one_way_client_pipe.close()


@pytest.fixture
async def protocol_factory_two_way_client_pipe(echo_requester) -> StreamClientProtocolFactory:
    factory = StreamClientProtocolFactory(
        requester=echo_requester,
        dataformat=JSONObject)
    yield factory


@pytest.fixture
async def protocol_factory_two_way_client_pipe_started(protocol_factory_two_way_client_pipe, initial_client_context, pipe_path) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    await protocol_factory_two_way_client_pipe.start()
    if not protocol_factory_two_way_client_pipe.full_name:
        protocol_factory_two_way_client_pipe.set_name(f'Pipe Client {pipe_path}', 'pipe')
    yield protocol_factory_two_way_client_pipe
    await protocol_factory_two_way_client_pipe.close()


@pytest.fixture
async def udp_protocol_factory_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action) -> DatagramServerProtocolFactory:
    factory = DatagramServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        hostname_lookup=True
    )
    yield factory


@pytest.fixture
async def udp_protocol_factory_one_way_server_started(udp_protocol_factory_one_way_server, server_sock_str,
                                                      udp_initial_server_context) -> DatagramServerProtocolFactory:
    context_cv.set(udp_initial_server_context)
    await udp_protocol_factory_one_way_server.start()
    if not udp_protocol_factory_one_way_server.full_name:
        udp_protocol_factory_one_way_server.set_name(f'UDP Server {server_sock_str}', 'udp')
    yield udp_protocol_factory_one_way_server
    if udp_protocol_factory_one_way_server.transport and not udp_protocol_factory_one_way_server.transport.is_closing():
        await udp_protocol_factory_one_way_server.close()


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
async def udp_protocol_factory_one_way_client() -> DatagramClientProtocolFactory:
    factory = DatagramClientProtocolFactory(
        dataformat=JSONObject,
        hostname_lookup=True)
    yield factory


@pytest.fixture
async def udp_protocol_factory_one_way_client_started(udp_protocol_factory_one_way_client, udp_initial_client_context, server_sock_str) -> DatagramClientProtocolFactory:
    context_cv.set(udp_initial_client_context)
    await udp_protocol_factory_one_way_client.start()
    if not udp_protocol_factory_one_way_client.full_name:
        udp_protocol_factory_one_way_client.set_name(f'UDP Client {server_sock_str}', 'udp')
    yield udp_protocol_factory_one_way_client
    if udp_protocol_factory_one_way_client.transport and not udp_protocol_factory_one_way_client.transport.is_closing():
        await udp_protocol_factory_one_way_client.close()


@pytest.fixture
async def udp_protocol_factory_two_way_client(echo_requester) -> DatagramClientProtocolFactory:
    factory = DatagramClientProtocolFactory(
        requester=echo_requester,
        dataformat=JSONObject,
        hostname_lookup=True)
    yield factory


@pytest.fixture
async def udp_protocol_factory_two_way_client_started(udp_protocol_factory_two_way_client, server_sock_str,
                                                      udp_initial_client_context) -> DatagramClientProtocolFactory:
    context_cv.set(udp_initial_client_context)
    await udp_protocol_factory_two_way_client.start()
    if not udp_protocol_factory_two_way_client.full_name:
        udp_protocol_factory_two_way_client.set_name(f'UDP Client {server_sock_str}', 'udp')
    yield udp_protocol_factory_two_way_client
    if udp_protocol_factory_two_way_client.transport and not udp_protocol_factory_two_way_client.transport.is_closing():
        await udp_protocol_factory_two_way_client.close()


@pytest.fixture
async def tcp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                      initial_server_context, server_sock_str) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=buffered_file_storage_action,
                               parent_name=f"TCP Server {server_sock_str}", peer_prefix='tcp',
                               preaction=buffered_file_storage_recording_action, hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_one_way_client(initial_client_context, server_sock_str) -> TCPClientConnection:
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(dataformat=JSONObject, peer_prefix='tcp', parent_name=f"TCP Client {server_sock_str}",
                               hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_server(echo_action, buffered_file_storage_recording_action, server_sock_str,
                                      initial_server_context) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=echo_action,
                               parent_name=f"TCP Server {server_sock_str}", peer_prefix='tcp',
                               preaction=buffered_file_storage_recording_action,
                               hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_client(echo_requester, initial_client_context, server_sock_str) -> TCPClientConnection:
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(requester=echo_requester, dataformat=JSONObject, peer_prefix='tcp',
                               parent_name=f"TCP Client {server_sock_str}", hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def udp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                      udp_initial_server_context, server_sock_str) -> UDPServerConnection:
    context_cv.set(udp_initial_server_context)
    conn = UDPServerConnection(dataformat=JSONObject, action=buffered_file_storage_action,
                               parent_name=f"UDP Server {server_sock_str}", peer_prefix='udp',
                               preaction=buffered_file_storage_recording_action, hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def udp_protocol_one_way_client(udp_initial_client_context, server_sock_str) -> UDPClientConnection:
    context_cv.set(udp_initial_client_context)
    conn = UDPClientConnection(dataformat=JSONObject, peer_prefix='udp', parent_name=f"UDP Client {server_sock_str}",
                               hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def udp_protocol_two_way_server(echo_action, buffered_file_storage_recording_action, server_sock_str,
                                      udp_initial_server_context) -> UDPServerConnection:
    context_cv.set(udp_initial_server_context)
    conn = UDPServerConnection(dataformat=JSONObject, action=echo_action,
                               parent_name=f"UDP Server {server_sock_str}", peer_prefix='udp',
                               preaction=buffered_file_storage_recording_action,
                               hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await asyncio.wait_for(conn.wait_closed(), timeout=1)


@pytest.fixture
async def udp_protocol_two_way_client(echo_requester, udp_initial_client_context, server_sock_str) -> UDPClientConnection:
    context_cv.set(udp_initial_client_context)
    conn = UDPClientConnection(requester=echo_requester, dataformat=JSONObject, peer_prefix='udp',
                               parent_name=f"UDP Client {server_sock_str}", hostname_lookup=True)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
def protocol_factory(connection_args):
    return connection_args[0]


@pytest.fixture
def connection(connection_args):
    return connection_args[1]


@pytest.fixture
def transport(connection_args):
    return connection_args[2]


@pytest.fixture
def adaptor(connection_args):
    return connection_args[3]


@pytest.fixture
def peer_data(connection_args):
    return connection_args[4]


@pytest.fixture
def connection_is_stored(connection_args):
    return connection_args[5]


@pytest.fixture
def protocol_name(connection_args):
    return connection_args[6]


@pytest.fixture(params=[
    lazy_fixture((
                 protocol_factory_one_way_server_started.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
                 one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] + ["tcp"],
    lazy_fixture((protocol_factory_one_way_client_started.__name__, tcp_protocol_one_way_client.__name__,
                  tcp_transport_client.__name__, one_way_sender_adaptor.__name__, server_sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            protocol_factory_two_way_server_started.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] + ["tcp"],
    lazy_fixture((protocol_factory_two_way_client_started.__name__, tcp_protocol_two_way_client.__name__,
                  tcp_transport_client.__name__, two_way_sender_adaptor.__name__, server_sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_one_way_server_started.__name__, udp_protocol_one_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True]  +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_one_way_client_started.__name__, udp_protocol_one_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_one_way_sender_adaptor.__name__, server_sock.__name__)) + [True] + [
        "udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_server_started.__name__, udp_protocol_two_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_client_started.__name__, udp_protocol_two_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_two_way_sender_adaptor.__name__, server_sock.__name__)) + [True] + [
        "udp"],
])
def connection_args(request):
    return request.param


@pytest.fixture
def two_way_server_protocol_factory(two_way_server_connection_args):
    return two_way_server_connection_args[0]


@pytest.fixture
def two_way_server_connection(two_way_server_connection_args):
    return two_way_server_connection_args[1]


@pytest.fixture
def two_way_server_transport(two_way_server_connection_args):
    return two_way_server_connection_args[2]


@pytest.fixture
def two_way_server_adaptor(two_way_server_connection_args):
    return two_way_server_connection_args[3]


@pytest.fixture
def two_way_server_protocol_name(two_way_server_connection_args):
    return two_way_server_connection_args[6]


@pytest.fixture(params=[
    lazy_fixture((
            protocol_factory_two_way_server_started.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_two_way_server_started.__name__, udp_protocol_two_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_receiver_adaptor.__name__, server_sock.__name__)) + [True] +
    ["udp"],
])
def two_way_server_connection_args(request):
    return request.param


@pytest.fixture
def two_way_client_protocol_factory(two_way_client_connection_args):
    return two_way_client_connection_args[0]


@pytest.fixture
def two_way_client_connection(two_way_client_connection_args):
    return two_way_client_connection_args[1]


@pytest.fixture
def two_way_client_transport(two_way_client_connection_args):
    return two_way_client_connection_args[2]


@pytest.fixture
def two_way_client_protocol_name(two_way_server_connection_args):
    return two_way_server_connection_args[6]


@pytest.fixture(params=[
    lazy_fixture((
            protocol_factory_two_way_client_started.__name__, tcp_protocol_two_way_client.__name__,
            tcp_transport_client.__name__, two_way_sender_adaptor.__name__, server_sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_two_way_client_started.__name__, udp_protocol_two_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_two_way_sender_adaptor.__name__, server_sock.__name__)) + [True] +
    ["udp"],
])
def two_way_client_connection_args(request):
    return request.param


@pytest.fixture
def one_way_server_protocol_factory(one_way_server_connection_args):
    return one_way_server_connection_args[0]


@pytest.fixture
def one_way_server_connection(one_way_server_connection_args):
    return one_way_server_connection_args[1]


@pytest.fixture
def one_way_server_transport(one_way_server_connection_args):
    return one_way_server_connection_args[2]


@pytest.fixture
def one_way_server_protocol_name(one_way_server_connection_args):
    return one_way_server_connection_args[6]


@pytest.fixture(params=[
    lazy_fixture((
            protocol_factory_one_way_server_started.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
            one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_one_way_server_started.__name__, udp_protocol_one_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] +
    ["udp"],
])
def one_way_server_connection_args(request):
    return request.param


@pytest.fixture
def one_way_client_protocol_factory(one_way_client_connection_args):
    return one_way_client_connection_args[0]


@pytest.fixture
def one_way_client_connection(one_way_client_connection_args):
    return one_way_client_connection_args[1]


@pytest.fixture
def one_way_client_transport(one_way_client_connection_args):
    return one_way_client_connection_args[2]


@pytest.fixture
def one_way_client_protocol_name(one_way_client_connection_args):
    return one_way_client_connection_args[6]


@pytest.fixture(params=[
    lazy_fixture((
            protocol_factory_one_way_client_started.__name__, tcp_protocol_one_way_client.__name__,
            tcp_transport_client.__name__, one_way_sender_adaptor.__name__, server_sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_one_way_client_started.__name__, udp_protocol_one_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_one_way_sender_adaptor.__name__, server_sock.__name__)) + [True] +
    ["udp"],
])
def one_way_client_connection_args(request):
    return request.param


@pytest.fixture
def stream_protocol_factory(stream_connection_args):
    return stream_connection_args[0]


@pytest.fixture
def stream_connection(stream_connection_args):
    return stream_connection_args[1]


@pytest.fixture
def stream_transport(stream_connection_args):
    return stream_connection_args[2]


@pytest.fixture
def stream_connection_is_stored(stream_connection_args):
    return stream_connection_args[5]


@pytest.fixture(params=[
    lazy_fixture((
            protocol_factory_one_way_server_started.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
            one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] + ["tcp"],
    lazy_fixture((
            protocol_factory_one_way_client_started.__name__, tcp_protocol_one_way_client.__name__,
            tcp_transport_client.__name__, one_way_sender_adaptor.__name__, server_sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            protocol_factory_two_way_server_started.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] + ["tcp"],
    lazy_fixture((protocol_factory_two_way_client_started.__name__, tcp_protocol_two_way_client.__name__,
                  tcp_transport_client.__name__, two_way_sender_adaptor.__name__, server_sock.__name__)) + [False] + ["tcp"],
])
def stream_connection_args(request):
    return request.param


@pytest.fixture
def datagram_protocol_factory(datagram_connection_args):
    return datagram_connection_args[0]


@pytest.fixture
def datagram_connection(datagram_connection_args):
    return datagram_connection_args[1]


@pytest.fixture
def datagram_transport(datagram_connection_args):
    return datagram_connection_args[2]


@pytest.fixture
def datagram_peer_data(datagram_connection_args):
    return datagram_connection_args[4]


@pytest.fixture
def datagram_connection_is_stored(datagram_connection_args):
    return datagram_connection_args[5]


@pytest.fixture(params=[
    lazy_fixture((
            udp_protocol_factory_one_way_server_started.__name__, udp_protocol_one_way_server.__name__,
            udp_transport_server.__name__, udp_one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_one_way_client_started.__name__, udp_protocol_one_way_client.__name__,
            udp_transport_client.__name__, udp_one_way_sender_adaptor.__name__, server_sock.__name__)) + [True] + [
        "udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_server_started.__name__, udp_protocol_two_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_receiver_adaptor.__name__, client_sock.__name__)) + [True] +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_client_started.__name__, udp_protocol_two_way_client.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_sender_adaptor.__name__, server_sock.__name__)) + [True] + [
        "udp"],
])
def datagram_connection_args(request):
    return request.param


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
                                                                   server_sock_str, sftp_initial_server_context) -> SFTPOSAuthProtocolFactory:
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
async def sftp_protocol_factory_client_started(sftp_initial_client_context, sftp_protocol_factory_client, tmpdir, server_sock_str) -> SFTPClientProtocolFactory:
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
    protocol = SFTPClientProtocol(dataformat=JSONObject, peer_prefix='sftp', parent_name=f"SFTP Client {server_sock_str}",
                                  base_path=Path(tmpdir) / 'sftp_sent', hostname_lookup=True)
    yield protocol
    if not protocol.is_closing():
        protocol.close()
        await protocol.wait_closed()


@pytest.fixture
def sftp_conn_server(request, extra_server_inet_sftp, sftp_protocol) -> MockSFTPConn:
    if is_lazy_fixture(sftp_protocol):
        sftp_protocol = request.getfixturevalue(sftp_protocol.name)
    yield MockSFTPConn(sftp_protocol, extra=extra_server_inet_sftp)


@pytest.fixture
def server_sftp_conn(extra_server_inet_sftp, sftp_protocol_one_way_server) -> MockSFTPConn:
    yield MockSFTPConn(sftp_protocol_one_way_server, extra=extra_server_inet_sftp)


@pytest.fixture
def sftp_conn_client(request, extra_client_inet_sftp, sftp_protocol) -> MockSFTPConn:
    if is_lazy_fixture(sftp_protocol):
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
    if is_lazy_fixture(sftp_conn):
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


@pytest.fixture(params=[
    lazy_fixture((
                 sftp_protocol_factory_server_started.__name__, sftp_protocol_one_way_server.__name__,
                 sftp_conn_server.__name__, sftp_one_way_receiver_adaptor.__name__, client_sock.__name__)) + [True],
    lazy_fixture((sftp_protocol_factory_client_started.__name__, sftp_protocol_one_way_client.__name__,
                  sftp_conn_client.__name__, sftp_one_way_sender_adaptor.__name__, server_sock.__name__)) + [False],
])
def sftp_connection_args(request):
    return request.param


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
def server_side_ssl(ssl_server_cert, ssl_server_key, ssl_client_cert, ssl_client_dir) -> ServerSideSSL:
    return ServerSideSSL(ssl=True, cert_required=True, check_hostname=True, cert=ssl_server_cert, key=ssl_server_key,
                         cafile=ssl_client_cert, capath=ssl_client_dir)


@pytest.fixture
def client_side_ssl(ssl_client_cert, ssl_client_key, ssl_server_cert, ssl_server_dir) -> ClientSideSSL:
    return ClientSideSSL(ssl=True, cert_required=True, check_hostname=True, cert=ssl_client_cert, key=ssl_client_key,
                         cafile=ssl_server_cert, capath=ssl_server_dir, cadata=ssl_server_cert.read_text())


@pytest.fixture
def client_side_ssl_no_cadata(ssl_client_cert, ssl_client_key, ssl_server_cert, ssl_server_dir) -> ClientSideSSL:
    return ClientSideSSL(ssl=True, cert_required=True, check_hostname=True, cert=ssl_client_cert, key=ssl_client_key,
                         cafile=ssl_server_cert, capath=ssl_server_dir)


@pytest.fixture
def server_side_no_ssl():
    return ServerSideSSL(ssl=False)


@pytest.fixture(params=[
    lazy_fixture(server_side_ssl.__name__),
    lazy_fixture(client_side_ssl.__name__),
])
def ssl_object(request):
    return request.param


@pytest.fixture
async def tcp_protocol_two_way_server_allowed_senders(echo_action, initial_server_context, server_sock, server_sock_ipv6,
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
async def udp_protocol_factory_allowed_senders(echo_action, server_sock, server_sock_ipv6) -> DatagramServerProtocolFactory:
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
