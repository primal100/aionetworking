import pytest
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, List, Tuple

from lib.conf.context import context_cv
from lib.conf.logging import connection_logger_cv, logger_cv
from lib.networking.adaptors import ReceiverAdaptor, SenderAdaptor
from lib.networking.connections import TCPServerConnection, TCPClientConnection
from lib.networking.connections_manager import ConnectionsManager
from lib.networking.protocol_factories import StreamServerProtocolFactory, StreamClientProtocolFactory
from lib.networking.types import SimpleNetworkConnectionType


from tests.mock import MockTCPTransport
from tests.test_actions.conftest import *
from tests.test_logging.conftest import *


@pytest.fixture
async def connections_manager() -> ConnectionsManager:
    from lib.networking.connections_manager import connections_manager
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
def simple_network_connections(queue, peer_str) -> List[SimpleNetworkConnectionType]:
    return [SimpleNetworkConnection(peer_str, "TCP Server 127.0.0.1:8888", queue),
            SimpleNetworkConnection('127.0.0.1:4444', "TCP Server 127.0.0.1:8888", queue)]


@pytest.fixture
def simple_network_connection(simple_network_connections) -> SimpleNetworkConnectionType:
    return simple_network_connections[0]


@pytest.fixture
def one_way_receiver_adaptor(object_class, buffered_file_storage_action, buffered_file_storage_recording_action, context,
                             receiver_connection_logger) -> ReceiverAdaptor:
    context_cv.set(context)
    connection_logger_cv.set(receiver_connection_logger)
    return ReceiverAdaptor(object_class, action=buffered_file_storage_action,
                           preaction=buffered_file_storage_recording_action)


@pytest.fixture
async def one_way_sender_adaptor(object_class, context_client, sender_connection_logger, deque) -> SenderAdaptor:
    context_cv.set(context_client)
    connection_logger_cv.set(sender_connection_logger)
    yield SenderAdaptor(object_class, send=deque.append)


@pytest.fixture
async def file_containing_json_recording(tmpdir, buffer_codec, json_encoded_multi, timestamp) -> Path:
    obj1 = buffer_codec.from_decoded(json_encoded_multi[0], received_timestamp=timestamp)
    await asyncio.sleep(1)
    obj2 = buffer_codec.from_decoded(json_encoded_multi[1],
                                     received_timestamp=timestamp + timedelta(seconds=1, microseconds=200))
    p = Path(tmpdir.mkdir("recording") / "json.recording")
    p.write_bytes(obj1.encoded + obj2.encoded)
    return p


@pytest.fixture
def protocol_factory_one_way_server(buffered_file_storage_recording_action, buffered_file_storage_action_binary,
                                    receiver_logger, object_class) -> StreamServerProtocolFactory:
    logger_cv.set(receiver_logger)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action_binary,
        dataformat=object_class)
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory


@pytest.fixture
def protocol_factory_one_way_client(sender_logger, object_class) -> StreamClientProtocolFactory:
    logger_cv.set(sender_logger)
    factory = StreamClientProtocolFactory(
        dataformat=object_class)
    if not factory.full_name:
        factory.set_name('TCP Client 127.0.0.1:0', 'tcp')
    yield factory


@pytest.fixture
async def tcp_protocol_one_way_server(buffered_file_storage_action_binary, buffered_file_storage_recording_action,
                                      receiver_logger, object_class, context) -> TCPServerConnection:
    logger_cv.set(receiver_logger)
    context_cv.set(context)
    yield TCPServerConnection(dataformat=object_class, action=buffered_file_storage_action,
                                    parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp',
                                    preaction=buffered_file_storage_recording_action)


@pytest.fixture
async def tcp_protocol_one_way_client(sender_logger, object_class, client_context) -> TCPClientConnection:
    logger_cv.set(sender_logger)
    context_cv.set(client_context)
    yield TCPClientConnection(dataformat=object_class, peer_prefix='tcp', parent_name="TCP Client 127.0.0.1:0")


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


@pytest.fixture(params=[(protocol_factory_one_way_server, tcp_protocol_one_way_server, tcp_transport, one_way_receiver_adaptor, peername, True),
                        (protocol_factory_one_way_client, tcp_protocol_one_way_client, tcp_transport_client, one_way_sender_adaptor, sock, False)])
def connection_args(request):
    return request.param


@pytest.fixture
def protocol_factory(request, connection_args):
    return get_fixture(request, connection_args[0])


@pytest.fixture
def connection(request, connection_args):
    return get_fixture(request, connection_args[1])


@pytest.fixture
def transport(request, connection_args):
    return get_fixture(request, connection_args[2])


@pytest.fixture
def adaptor(request, connection_args):
    return get_fixture(request, connection_args[3])


@pytest.fixture
def peer_data(request, connection_args):
    return get_fixture(request, connection_args[4])


@pytest.fixture
def connection_is_stored(connection_args):
    return connection_args[5]
