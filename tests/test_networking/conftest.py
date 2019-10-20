from pytest_lazyfixture import lazy_fixture, is_lazy_fixture
import datetime
import os

from lib.conf.context import context_cv
from lib.networking.adaptors import ReceiverAdaptor, SenderAdaptor
from lib.networking.connections import (TCPServerConnection, TCPClientConnection,
                                        UDPServerConnection, UDPClientConnection)
from lib.networking.protocol_factories import (StreamServerProtocolFactory, StreamClientProtocolFactory,
                                               DatagramServerProtocolFactory, DatagramClientProtocolFactory,
                                               BaseProtocolFactory)
from lib.networking.sftp import SFTPClientProtocolFactory, SFTPFactory, SFTPClientProtocol
from lib.networking.sftp_os_auth import SFTPOSAuthProtocolFactory, SFTPServerOSAuthProtocol
from lib.networking.transports import DatagramTransportWrapper
from lib.compatibility_tests import AsyncMock

from typing import Union

from tests.mock import MockTCPTransport, MockDatagramTransport, MockAFInetSocket, MockAFUnixSocket, MockSFTPConn

from tests.test_actions.conftest import *   ###Required for tests
from tests.test_logging.conftest import *
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
        return sftp_username_password
    elif os.name == 'nt':
        import pywintypes
        import win32con
        user, password = sftp_username_password
        return (user, '.', password, win32con.LOGON32_LOGON_BATCH, win32con.LOGON32_PROVIDER_DEFAULT)


@pytest.fixture
def critical_logging_only(caplog):
    caplog.set_level(logging.CRITICAL, logger="receiver.connection")


@pytest.fixture
def initial_server_context() -> Dict[str, Any]:
    return {'endpoint': 'TCP Server 127.0.0.1:8888'}


@pytest.fixture
def initial_client_context() -> Dict[str, Any]:
    return {'endpoint': 'TCP Client 127.0.0.1:0'}


@pytest.fixture
def udp_initial_server_context() -> Dict[str, Any]:
    return {'endpoint': 'UDP Server 127.0.0.1:8888'}


@pytest.fixture
def udp_initial_client_context() -> Dict[str, Any]:
    return {'endpoint': 'UDP Client 127.0.0.1:0'}


@pytest.fixture
def sftp_initial_server_context() -> Dict[str, Any]:
    return {'endpoint': 'SFTP Server 127.0.0.1:8888'}


@pytest.fixture
def sftp_initial_client_context() -> Dict[str, Any]:
    return {'endpoint': 'SFTP Client 127.0.0.1:0'}


@pytest.fixture
def context() -> Dict[str, Any]:
    return {'protocol_name': 'TCP Server', 'endpoint': 'TCP Server 127.0.0.1:8888', 'host': '127.0.0.1', 'port': 60000,
            'peer': '127.0.0.1:60000', 'sock': '127.0.0.1:8888', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000'}


@pytest.fixture
def client_context() -> dict:
    return {'protocol_name': 'TCP Client', 'endpoint': 'TCP Client 127.0.0.1:0', 'host': '127.0.0.1', 'port': 8888,
            'peer': '127.0.0.1:8888', 'sock': '127.0.0.1:60000', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000'}


@pytest.fixture
def udp_server_context() -> Dict[str, Any]:
    return {'protocol_name': 'UDP Server', 'endpoint': 'UDP Server 127.0.0.1:8888', 'host': '127.0.0.1', 'port': 60000,
            'peer': '127.0.0.1:60000', 'sock': '127.0.0.1:8888', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000'}


@pytest.fixture
def udp_client_context() -> dict:
    return {'protocol_name': 'UDP Client', 'endpoint': 'UDP Client 127.0.0.1:0', 'host': '127.0.0.1', 'port': 8888,
            'peer': '127.0.0.1:8888', 'sock': '127.0.0.1:60000', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000'}


@pytest.fixture
def sftp_server_context() -> Dict[str, Any]:
    return {'protocol_name': 'SFTP Server', 'endpoint': 'SFTP Server 127.0.0.1:8888', 'host': '127.0.0.1', 'port': 60000,
            'peer': '127.0.0.1:60000', 'sock': '127.0.0.1:8888', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000', 'username': 'testuser'}


@pytest.fixture
def sftp_client_context() -> dict:
    return {'protocol_name': 'SFTP Client', 'endpoint': 'SFTP Client 127.0.0.1:0', 'host': '127.0.0.1', 'port': 8888,
            'peer': '127.0.0.1:8888', 'sock': '127.0.0.1:60000', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000', 'username': 'testuser'}


@pytest.fixture
def json_client_codec(client_context) -> JSONCodec:
    return JSONCodec(JSONObject, context=client_context)


@pytest.fixture
def echo_decode_error_response_encoded(echo_exception_request_encoded) -> bytes:
    return b'{"error": "JSON was invalid"}'


@pytest.fixture
def echo_recording_data() -> List:
    return [recorded_packet(sent_by_server=False, timestamp=datetime.datetime(2019, 1, 1, 1, 1), sender='127.0.0.1', data=b'{"id": 1, "method": "echo"}')]


@pytest.fixture
async def one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action, context) -> ReceiverAdaptor:
    context_cv.set(context)
    adaptor = ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                              preaction=buffered_file_storage_recording_action)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def one_way_sender_adaptor(context_client,queue) -> SenderAdaptor:
    context_cv.set(context_client)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def two_way_receiver_adaptor(echo_action, buffered_file_storage_recording_action, context, queue) -> ReceiverAdaptor:
    context_cv.set(context)
    adaptor = ReceiverAdaptor(JSONObject, action=echo_action, preaction=buffered_file_storage_recording_action,
                              send=queue.put_nowait)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def two_way_sender_adaptor(echo_requester, context_client, queue) -> SenderAdaptor:
    context_cv.set(context_client)
    adaptor = SenderAdaptor(JSONObject, send=queue.put_nowait, requester=echo_requester)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action, context) -> ReceiverAdaptor:
    context_cv.set(context)
    adaptor = ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                              preaction=buffered_file_storage_recording_action)
    yield adaptor
    await adaptor.close()


@pytest.fixture
async def one_way_sender_adaptor(context_client,queue) -> SenderAdaptor:
    context_cv.set(context_client)
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
    obj1 = buffer_codec.from_decoded(json_encoded_multi[0], received_timestamp=timestamp)
    await asyncio.sleep(1)
    obj2 = buffer_codec.from_decoded(json_encoded_multi[1],
                                     received_timestamp=timestamp + datetime.timedelta(seconds=1, microseconds=200000))
    p = Path(tmpdir.mkdir("recording") / "json.recording")
    p.write_bytes(obj1.encoded + obj2.encoded)
    return p


@pytest.fixture
def extra_inet(peername, sock) -> dict:
    return {'peername': peername, 'sockname': sock, 'socket': MockAFInetSocket()}


@pytest.fixture
def extra_client_inet(peername, sock) -> dict:
    return {'peername': sock, 'sockname': peername, 'socket': MockAFInetSocket()}


@pytest.fixture
def extra_server_inet_sftp(peername, sock) -> dict:
    return {'peername': peername, 'sockname': sock, 'socket': MockAFInetSocket(),
            'username': 'testuser'}


@pytest.fixture
def extra_client_inet_sftp(peername, sock) -> dict:
    return {'peername': sock, 'sockname': peername, 'socket': MockAFInetSocket(), 'username': 'testuser'}


@pytest.fixture
def extra_unix(peername, sock) -> dict:
    return {'peername': peername, 'sockname': sock, 'socket': MockAFUnixSocket()}


@pytest.fixture
def extra_client_unix(peername, sock) -> dict:
    return {'peername': sock, 'sockname': peername, 'socket': MockAFUnixSocket()}


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
    yield MockDatagramTransport(queue, extra=extra_inet)


@pytest.fixture
async def udp_transport_client(queue, extra_client_inet) -> MockDatagramTransport:
    yield MockDatagramTransport(queue, extra=extra_client_inet)


@pytest.fixture
async def udp_transport_wrapper_server(udp_transport_server, queue, peername) -> DatagramTransportWrapper:
    yield DatagramTransportWrapper(udp_transport_server, peername)


@pytest.fixture
async def udp_transport_wrapper_client(udp_transport_client, sock) -> DatagramTransportWrapper:
    yield DatagramTransportWrapper(udp_transport_client, sock)


@pytest.fixture
def peername() -> Tuple[str, int]:
    return '127.0.0.1', 60000


@pytest.fixture
def sock() -> Tuple[str, int]:
    return '127.0.0.1', 8888


@pytest.fixture
def true() -> bool:
    return True


@pytest.fixture
def false() -> bool:
    return False


@pytest.fixture
async def protocol_factory_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                          initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory
    await factory.close()


@pytest.fixture
async def protocol_factory_two_way_server(echo_action, buffered_file_storage_recording_action,
                                          initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=echo_action,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory
    await factory.close()


@pytest.fixture
async def protocol_factory_one_way_client(initial_client_context) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('TCP Client 127.0.0.1:0', 'tcp')
    yield factory
    await factory.close()


@pytest.fixture
async def protocol_factory_two_way_client(echo_requester, initial_client_context) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    factory = StreamClientProtocolFactory(
        requester=echo_requester,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('TCP Client 127.0.0.1:0', 'tcp')
    yield factory
    await factory.close()


@pytest.fixture
async def udp_protocol_factory_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                              udp_initial_server_context) -> DatagramServerProtocolFactory:
    context_cv.set(udp_initial_server_context)
    factory = DatagramServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('UDP Server 127.0.0.1:8888', 'udp')
    yield factory
    if factory.transport and not factory.transport.is_closing():
        await factory.close()


@pytest.fixture
async def udp_protocol_factory_two_way_server(echo_action, buffered_file_storage_recording_action,
                                              udp_initial_server_context) -> DatagramServerProtocolFactory:
    context_cv.set(udp_initial_server_context)
    factory = DatagramServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=echo_action,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('UDP Server 127.0.0.1:8888', 'udp')
    yield factory
    if factory.transport and not factory.transport.is_closing():
        await factory.close()


@pytest.fixture
async def udp_protocol_factory_one_way_client(udp_initial_client_context) -> DatagramClientProtocolFactory:
    context_cv.set(udp_initial_client_context)
    factory = DatagramClientProtocolFactory(
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('UDP Client 127.0.0.1:0', 'udp')
    yield factory
    if factory.transport and not factory.transport.is_closing():
        await factory.close()


@pytest.fixture
async def udp_protocol_factory_two_way_client(echo_requester, udp_initial_client_context) -> DatagramClientProtocolFactory:
    context_cv.set(udp_initial_client_context)
    factory = DatagramClientProtocolFactory(
        requester=echo_requester,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('UDP Client 127.0.0.1:0', 'udp')
    yield factory
    if factory.transport and not factory.transport.is_closing():
        await factory.close()


@pytest.fixture
async def tcp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                      initial_server_context) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=buffered_file_storage_action,
                               parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp',
                               preaction=buffered_file_storage_recording_action)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_one_way_client(initial_client_context) -> TCPClientConnection:
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(dataformat=JSONObject, peer_prefix='tcp', parent_name="TCP Client 127.0.0.1:0")
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_server(echo_action, buffered_file_storage_recording_action,
                                      initial_server_context) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=echo_action,
                               parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp',
                               preaction=buffered_file_storage_recording_action)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_client(echo_requester, initial_client_context) -> TCPClientConnection:
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(requester=echo_requester, dataformat=JSONObject, peer_prefix='tcp',
                               parent_name="TCP Client 127.0.0.1:0")
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def udp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                      udp_initial_server_context) -> UDPServerConnection:
    context_cv.set(udp_initial_server_context)
    conn = UDPServerConnection(dataformat=JSONObject, action=buffered_file_storage_action,
                               parent_name="UDP Server 127.0.0.1:8888", peer_prefix='udp',
                               preaction=buffered_file_storage_recording_action)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def udp_protocol_one_way_client(udp_initial_client_context) -> UDPClientConnection:
    context_cv.set(udp_initial_client_context)
    conn = UDPClientConnection(dataformat=JSONObject, peer_prefix='udp', parent_name="UDP Client 127.0.0.1:0")
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await conn.wait_closed()


@pytest.fixture
async def udp_protocol_two_way_server(echo_action, buffered_file_storage_recording_action,
                                      udp_initial_server_context) -> UDPServerConnection:
    context_cv.set(udp_initial_server_context)
    conn = UDPServerConnection(dataformat=JSONObject, action=echo_action,
                               parent_name="UDP Server 127.0.0.1:8888", peer_prefix='udp',
                               preaction=buffered_file_storage_recording_action)
    yield conn
    if conn.transport and not conn.transport.is_closing():
        conn.transport.close()
    await asyncio.wait_for(conn.wait_closed(), timeout=1)


@pytest.fixture
async def udp_protocol_two_way_client(echo_requester, udp_initial_client_context) -> UDPClientConnection:
    context_cv.set(udp_initial_client_context)
    conn = UDPClientConnection(requester=echo_requester, dataformat=JSONObject, peer_prefix='udp',
                               parent_name="UDP Client 127.0.0.1:0")
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
                 protocol_factory_one_way_server.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
                 one_way_receiver_adaptor.__name__, peername.__name__)) + [True] + ["tcp"],
    lazy_fixture((protocol_factory_one_way_client.__name__, tcp_protocol_one_way_client.__name__,
                  tcp_transport_client.__name__, one_way_sender_adaptor.__name__, sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            protocol_factory_two_way_server.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, peername.__name__)) + [True] + ["tcp"],
    lazy_fixture((protocol_factory_two_way_client.__name__, tcp_protocol_two_way_client.__name__,
                  tcp_transport_client.__name__, two_way_sender_adaptor.__name__, sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_one_way_server.__name__, udp_protocol_one_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_one_way_receiver_adaptor.__name__, peername.__name__)) + [True]  +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_one_way_client.__name__, udp_protocol_one_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_one_way_sender_adaptor.__name__, sock.__name__)) + [True] + [
        "udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_server.__name__, udp_protocol_two_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_receiver_adaptor.__name__, peername.__name__)) + [True] +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_client.__name__, udp_protocol_two_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_two_way_sender_adaptor.__name__, sock.__name__)) + [True] + [
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
            protocol_factory_two_way_server.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, peername.__name__)) + [True] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_two_way_server.__name__, udp_protocol_two_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_receiver_adaptor.__name__, peername.__name__)) + [True] +
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
            protocol_factory_two_way_client.__name__, tcp_protocol_two_way_client.__name__,
            tcp_transport_client.__name__, two_way_sender_adaptor.__name__, sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_two_way_client.__name__, udp_protocol_two_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_two_way_sender_adaptor.__name__, sock.__name__)) + [True] +
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
            protocol_factory_one_way_server.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
            one_way_receiver_adaptor.__name__, peername.__name__)) + [True] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_one_way_server.__name__, udp_protocol_one_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_one_way_receiver_adaptor.__name__, peername.__name__)) + [True] +
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
            protocol_factory_one_way_client.__name__, tcp_protocol_one_way_client.__name__,
            tcp_transport_client.__name__, one_way_sender_adaptor.__name__, sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            udp_protocol_factory_one_way_client.__name__, udp_protocol_one_way_client.__name__,
            udp_transport_wrapper_client.__name__, udp_one_way_sender_adaptor.__name__, sock.__name__)) + [True] +
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
            protocol_factory_one_way_server.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
            one_way_receiver_adaptor.__name__, peername.__name__)) + [True] + ["tcp"],
    lazy_fixture((
            protocol_factory_one_way_client.__name__, tcp_protocol_one_way_client.__name__,
            tcp_transport_client.__name__, one_way_sender_adaptor.__name__, sock.__name__)) + [False] + ["tcp"],
    lazy_fixture((
            protocol_factory_two_way_server.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, peername.__name__)) + [True] + ["tcp"],
    lazy_fixture((protocol_factory_two_way_client.__name__, tcp_protocol_two_way_client.__name__,
                  tcp_transport_client.__name__, two_way_sender_adaptor.__name__, sock.__name__)) + [False] + ["tcp"],
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
            udp_protocol_factory_one_way_server.__name__, udp_protocol_one_way_server.__name__,
            udp_transport_server.__name__, udp_one_way_receiver_adaptor.__name__, peername.__name__)) + [True] +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_one_way_client.__name__, udp_protocol_one_way_client.__name__,
            udp_transport_client.__name__, udp_one_way_sender_adaptor.__name__, sock.__name__)) + [True] + [
        "udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_server.__name__, udp_protocol_two_way_server.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_receiver_adaptor.__name__, peername.__name__)) + [True] +
    ["udp"],
    lazy_fixture((
            udp_protocol_factory_two_way_client.__name__, udp_protocol_two_way_client.__name__,
            udp_transport_wrapper_server.__name__, udp_two_way_sender_adaptor.__name__, sock.__name__)) + [True] + [
        "udp"],
])
def datagram_connection_args(request):
    return request.param


@pytest.fixture
async def sftp_protocol_factory_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                               sftp_initial_server_context) -> SFTPOSAuthProtocolFactory:
    context_cv.set(sftp_initial_server_context)
    factory = SFTPOSAuthProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject)
    #await factory.start()
    if not factory.full_name:
        factory.set_name('SFTP Server 127.0.0.1:8888', 'sftp')
    yield factory
    await factory.close()


@pytest.fixture
async def sftp_protocol_factory_one_way_client(sftp_initial_client_context, tmpdir) -> SFTPClientProtocolFactory:
    context_cv.set(sftp_initial_client_context)
    factory = SFTPClientProtocolFactory(
        dataformat=JSONObject,
        base_path=Path(tmpdir) / 'sftp_sent',
    )
    #await factory.start()
    if not factory.full_name:
        factory.set_name('SFTP Client 127.0.0.1:0', 'sftp')
    yield factory
    await factory.close()


@pytest.fixture
def sftp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                 sftp_initial_server_context) -> SFTPServerOSAuthProtocol:
    context_cv.set(sftp_initial_server_context)
    protocol = SFTPServerOSAuthProtocol(dataformat=JSONObject, action=buffered_file_storage_action,
                               parent_name="SFTP Server 127.0.0.1:8888", peer_prefix='sftp',
                               preaction=buffered_file_storage_recording_action)
    yield protocol


@pytest.fixture
def sftp_protocol_one_way_client(sftp_initial_client_context, tmpdir) -> SFTPClientProtocol:
    context_cv.set(sftp_initial_client_context)
    conn = SFTPClientProtocol(dataformat=JSONObject, peer_prefix='sftp', parent_name="SFTP Client 127.0.0.1:0",
                              base_path=Path(tmpdir) / 'sftp_sent')
    yield conn


@pytest.fixture
def sftp_conn_server(request, extra_server_inet_sftp, sftp_protocol) -> MockSFTPConn:
    if is_lazy_fixture(sftp_protocol):
        sftp_protocol = request.getfixturevalue(sftp_protocol.name)
    yield MockSFTPConn(sftp_protocol, extra=extra_server_inet_sftp)


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
def sftp_factory_client(sftp_one_way_conn_client, tmpdir) -> SFTPFactory:
    path = Path(tmpdir) / "sftp_received"
    sftp_factory = SFTPFactory(sftp_one_way_conn_client, base_upload_dir=path)
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
                 sftp_protocol_factory_one_way_server.__name__, sftp_protocol_one_way_server.__name__,
                 sftp_conn_server.__name__, sftp_one_way_receiver_adaptor.__name__, peername.__name__)) + [True],
    lazy_fixture((sftp_protocol_factory_one_way_client.__name__, sftp_protocol_one_way_client.__name__,
                  sftp_conn_client.__name__, sftp_one_way_sender_adaptor.__name__, sock.__name__)) + [False],
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

