import pytest

from lib.conf.mapping import MappingConfig
from lib.actions.file_storage import FileStorage, BufferedFileStorage
from lib.actions.jsonrpc import SampleJSONRPCServer
from lib.formats.contrib.json import JSONObject
from lib.formats.contrib.TCAP_MAP import TCAPMAPASNObject
from lib.networking.tcp import TCPServerProtocol, TCPOneWayServerProtocol, TCPClientProtocol
from lib.networking.udp import UDPServerProtocol, UDPServerOneWayProtocol, UDPClientProtocol
from lib.receivers.asyncio_servers import TCPServer
from lib.receivers.asyncio_servers import UDPServer
from lib.requesters.jsonrpc import SampleJSONRPCClient
from lib.senders.asyncio_clients import TCPClient, UDPClient


@pytest.fixture
def json_rpc_action():
    yield SampleJSONRPCServer(timeout=3)


@pytest.fixture
def file_storage_action():
    from lib.settings import TEST_DATA_DIR
    yield FileStorage(base_path=TEST_DATA_DIR,
                      path='Encoded/{msg.protocol_name}/{msg.sender}_{msg.uid}.{msg.protocol_name}')


@pytest.fixture
def buffered_file_storage_action():
    from lib.settings import TEST_DATA_DIR
    yield BufferedFileStorage(base_path=TEST_DATA_DIR, path='Encoded/{msg.protocol_name}')


@pytest.fixture
def tcp_protocol(json_rpc_action):
    yield TCPServerProtocol(JSONObject, action=json_rpc_action, timeout=4, aliases={'127.0.0.1': 'localhost'})


@pytest.fixture
def tcp_one_way_protocol(file_storage_action):
    yield TCPOneWayServerProtocol(TCAPMAPASNObject, action=file_storage_action, aliases={'127.0.0.1': 'localhost', '127.0.0.2': 'localhost2'}, allowed_senders=('127.0.0.1', '127.0.0.2'))


@pytest.fixture
def udp_protocol(json_rpc_action):
    yield UDPServerProtocol(JSONObject, action=json_rpc_action, aliases={'127.0.0.1': 'localhost'})


@pytest.fixture
def udp_one_way_protocol(buffered_file_storage_action):
    yield UDPServerOneWayProtocol(TCAPMAPASNObject, action=buffered_file_storage_action, aliases={'127.0.0.1': 'localhost', '127.0.0.2': 'localhost2'}, allowed_senders=('127.0.0.1', '127.0.0.2'))


@pytest.fixture
def tcp_server(tcp_protocol):
    receiver = TCPServer(protocol=tcp_protocol)
    yield receiver


@pytest.fixture
def tcp_one_way_server(tcp_one_way_protocol):
    receiver = TCPServer(protocol=tcp_one_way_protocol)
    yield receiver


@pytest.fixture
def udp_server(udp_protocol):
    receiver = UDPServer(protocol=udp_protocol)
    yield receiver


@pytest.fixture
def udp_one_way_server(udp_one_way_protocol):
    receiver = UDPServer(protocol=udp_one_way_protocol)
    yield receiver


@pytest.fixture
def json_rpc_requester():
    yield SampleJSONRPCClient(timeout=3)


@pytest.fixture
def file_storage_action():
    yield FileStorage()


@pytest.fixture
def tcp_client_protocol(json_rpc_requester):
    yield TCPClientProtocol(JSONObject, action=json_rpc_action, timeout=4, aliases={'127.0.0.1': 'localhost'})


@pytest.fixture
def udp_client_protocol(file_storage_action):
    yield UDPClientProtocol(JSONObject, action=file_storage_action, timeout=3, aliases={'127.0.0.1': 'localhost', '127.0.0.2': 'localhost2'})


@pytest.fixture
def tcp_client(tcp_protocol):
    receiver = TCPClient(protocol=tcp_protocol)
    yield receiver


@pytest.fixture
def tcp_one_way_client(tcp_one_way_protocol):
    receiver = TCPClient(protocol=tcp_one_way_protocol)
    yield receiver


@pytest.fixture
def udp_client(udp_protocol):
    receiver = UDPClient(protocol=udp_protocol)
    yield receiver


@pytest.fixture
def udp_one_way_client(udp_one_way_protocol):
    receiver = UDPClient(protocol=udp_one_way_protocol)
    yield receiver


@pytest.fixture
def dict_parser():
    d = {

    }
    yield MappingConfig(d)


@pytest.fixture
def json_parser():
    pass


@pytest.fixture
def cp_parser():
    pass