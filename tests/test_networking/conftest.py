from pytest_lazyfixture import lazy_fixture
from datetime import timedelta, datetime

from lib.conf.context import context_cv
from lib.networking.adaptors import ReceiverAdaptor, SenderAdaptor
from lib.networking.connections import TCPServerConnection, TCPClientConnection
from lib.networking.protocol_factories import StreamServerProtocolFactory, StreamClientProtocolFactory

from tests.mock import MockTCPTransport

from tests.test_actions.conftest import *   ###Required for tests
from tests.test_logging.conftest import *
from tests.test_requesters.conftest import *


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
def client_context() -> dict:
    return {'protocol_name': 'TCP Client', 'endpoint': 'TCP Client 127.0.0.1:0', 'host': '127.0.0.1', 'port': 8888,
            'peer': '127.0.0.1:8888', 'sock': '127.0.0.1:60000', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000'}


@pytest.fixture
def json_client_codec(client_context) -> JSONCodec:
    return JSONCodec(JSONObject, context=client_context)


@pytest.fixture
def echo_decode_error_response_encoded(echo_exception_request_encoded) -> bytes:
    return b'{"error": "JSON was invalid"}'


@pytest.fixture
def echo_recording_data() -> List:
    return [recorded_packet(sent_by_server=False, timestamp=datetime(2019, 1, 1, 1, 1), sender='127.0.0.1', data=b'{"id": 1, "method": "echo"}')]


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
async def file_containing_json_recording(tmpdir, buffer_codec, json_encoded_multi, timestamp) -> Path:
    obj1 = buffer_codec.from_decoded(json_encoded_multi[0], received_timestamp=timestamp)
    await asyncio.sleep(1)
    obj2 = buffer_codec.from_decoded(json_encoded_multi[1],
                                     received_timestamp=timestamp + timedelta(seconds=1, microseconds=200000))
    p = Path(tmpdir.mkdir("recording") / "json.recording")
    p.write_bytes(obj1.encoded + obj2.encoded)
    return p


@pytest.fixture
def extra(peername, sock) -> dict:
    return {'peername': peername, 'sockname': sock}


@pytest.fixture
def extra_client(peername, sock) -> dict:
    return {'peername': sock, 'sockname': peername}


@pytest.fixture
async def tcp_transport(queue, extra) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra)


@pytest.fixture
async def tcp_transport_client(queue, extra_client) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra_client)


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
async def protocol_factory_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                          initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject)
    await factory.start()
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
    await factory.start()
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory
    await factory.close()


@pytest.fixture
async def protocol_factory_one_way_client(initial_client_context) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject)
    await factory.start()
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
    await factory.start()
    if not factory.full_name:
        factory.set_name('TCP Client 127.0.0.1:0', 'tcp')
    yield factory
    await factory.close()


@pytest.fixture
async def tcp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                      initial_server_context) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=buffered_file_storage_action,
                               parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp',
                               preaction=buffered_file_storage_recording_action)
    yield conn
    if not conn.is_closing():
        conn.connection_lost(None)
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_one_way_client(initial_client_context) -> TCPClientConnection:
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(dataformat=JSONObject, peer_prefix='tcp', parent_name="TCP Client 127.0.0.1:0")
    yield conn
    if not conn.is_closing():
        conn.connection_lost(None)
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_server(echo_action, buffered_file_storage_recording_action,
                                      initial_server_context) -> TCPServerConnection:
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=echo_action,
                               parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp',
                               preaction=buffered_file_storage_recording_action)
    yield conn
    if not conn.is_closing():
        conn.connection_lost(None)
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_two_way_client(echo_requester, initial_client_context) -> TCPClientConnection:
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(requester=echo_requester, dataformat=JSONObject, peer_prefix='tcp', parent_name="TCP Client 127.0.0.1:0")
    yield conn
    if not conn.is_closing():
        conn.connection_lost(None)
    await conn.wait_closed()


@pytest.fixture(params=[
    lazy_fixture((
                 protocol_factory_one_way_server.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
                 one_way_receiver_adaptor.__name__, peername.__name__)) + [True],
    lazy_fixture((protocol_factory_one_way_client.__name__, tcp_protocol_one_way_client.__name__,
                  tcp_transport_client.__name__, one_way_sender_adaptor.__name__, sock.__name__)) + [False],
    lazy_fixture((
            protocol_factory_two_way_server.__name__, tcp_protocol_two_way_server.__name__, tcp_transport.__name__,
            two_way_receiver_adaptor.__name__, peername.__name__)) + [True],
    lazy_fixture((protocol_factory_two_way_client.__name__, tcp_protocol_two_way_client.__name__,
                  tcp_transport_client.__name__, two_way_sender_adaptor.__name__, sock.__name__)) + [False],
])
def connection_args(request):
    return request.param
