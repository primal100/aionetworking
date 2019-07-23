from datetime import datetime
import asyncio
import collections
import pytest
import binascii
from pycrate_asn1dir.TCAP_MAP import TCAP_MAP_Messages
from pathlib import Path

from lib.actions.file_storage import FileStorage, BufferedFileStorage, ManagedFile
from lib.actions.jsonrpc import SampleJSONRPCServer
from lib.networking.tcp import TCPOneWayServerProtocol, TCPServerProtocol, TCPClientProtocol
#from lib.requesters.jsonrpc import SampleJSONRPCClient
from lib.formats.contrib.json import JSONObject, JSONCodec
from lib.formats.contrib.TCAP_MAP import TCAPMAPASNObject
from lib.formats.contrib.asn1 import PyCrateAsnCodec
from lib.wrappers.schedulers import TaskScheduler

from mock import MockTCPTransport, MockDatagramTransport

from typing import List, Tuple


@pytest.fixture
def context() -> dict:
    return {'protocol_name': 'TCP Server', 'peer': ('127.0.0.1', 8888), 'sock': ('127.0.0.1', 60000),
            'alias': '127.0.0.1', 'peer_ip': '127.0.0.1', 'peer_port': 8888, 'other': '127.0.0.1:8888',
            'own': '127.0.0.1:60000', 'server': '127.0.0.1:60000', 'client': '127.0.0.1:8888'}


@pytest.fixture
def asn_codec(context) -> PyCrateAsnCodec:
    return PyCrateAsnCodec(TCAPMAPASNObject, context=context,
                        asn_class=TCAPMAPASNObject.asn_class)


@pytest.fixture
def asn_buffer() -> bytes:
    return b"bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00e\x16H\x04\xa5\x05\x00\x01I\x04\x84\x00\x01\xffl\x08\xa1\x06\x02\x01\x02\x02\x018d<I\x04W\x18\x00\x00k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x05\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x08\xa3\x06\x02\x01\x01\x02\x01\x0b"


@pytest.fixture
def asn_encoded_multi() -> List[bytes]:
    hexes = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    return [binascii.unhexlify(h) for h in hexes]


@pytest.fixture
def asn_decoded_multi(asn_encoded_multi) -> List[Tuple]:
    decoder = TCAP_MAP_Messages.TCAP_MAP_Message
    decoded = []
    for encoded in asn_encoded_multi:
        decoder.from_ber(encoded)
        decoded.append(decoder())
    return decoded


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2019, 1, 1, 1, 1)


@pytest.fixture
def asn_objects(asn_encoded_multi, asn_decoded_multi, timestamp, context) -> List[TCAPMAPASNObject]:
    return [TCAPMAPASNObject(encoded, asn_decoded_multi[i], context=context,
                            received_timestamp=timestamp) for i, encoded in
           enumerate(asn_encoded_multi)]


@pytest.fixture
def asn_one_encoded() -> bytes:
    return b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0'


@pytest.fixture
def asn_one_decoded() -> Tuple:
    return ('begin', {'otid': b'\x00\x00\x00\x01', 'dialoguePortion': {
            'direct-reference': (0, 0, 17, 773, 1, 1, 1), 'encoding': ('single-ASN1-type', ('DialoguePDU', (
            'dialogueRequest', {'protocol-version': (1, 1), 'application-context-name': (0, 4, 0, 0, 1, 0, 20, 2)})))},
                                                                'components': [('basicROS', ('invoke', {
                                                                    'invokeId': ('present', -1),
                                                                    'opcode': ('local', 45), 'argument': (
                                                                    'RoutingInfoForSM-Arg',
                                                                    {'msisdn': b'\x91\x14\x97Bu3\xf3',
                                                                     'sm-RP-PRI': False,
                                                                     'serviceCentreAddress': b'\x91\x14\x97yy\x08\xf0'})}))]})


@pytest.fixture
def asn_object(asn_one_encoded, asn_one_decoded) -> TCAPMAPASNObject:
    return TCAPMAPASNObject(asn_one_encoded, asn_one_decoded, context=context,
                           received_timestamp=datetime(2019, 1, 1, 1, 1))


@pytest.fixture
def file_containing_asn(tmpdir, asn_one_encoded) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("testasn"))
    p.write_bytes(asn_one_encoded)
    return p


@pytest.fixture
def file_containing_multi_asn(tmpdir, asn_buffer) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("testasn"))
    p.write_bytes(asn_buffer)
    return p


@pytest.fixture
def json_codec() -> JSONCodec:
    return JSONCodec(JSONObject, context=context)


@pytest.fixture
def json_rpc_action() -> SampleJSONRPCServer:
    return SampleJSONRPCServer(timeout=3)

"""
@pytest.fixture
def json_rpc_requester() -> SampleJSONRPCClient:
    return SampleJSONRPCClient()"""


@pytest.fixture
async def managed_file_binary(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.get_file(path, timeout=None, mode='ab', separator=b'')
    yield f
    await f.close()


@pytest.fixture
async def managed_file_text(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.get_file(path, timeout=None, mode='a', separator='')
    yield f
    await f.close()


@pytest.fixture
async def managed_file_short_timeout(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.get_file(path, timeout=0.0001)
    yield f
    await f.close()


@pytest.fixture
def file_storage_action_binary(tmp_path) -> FileStorage:
    return FileStorage(base_path=tmp_path, binary=True,
                      path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')


@pytest.fixture
def buffered_file_storage_action_binary(tmp_path) -> BufferedFileStorage:
    return BufferedFileStorage(base_path=tmp_path, binary=True, path='Encoded/{msg.sender}_{msg.name}.{msg.name}')


@pytest.fixture
def file_storage_action_text(tmp_path) -> FileStorage:
    return FileStorage(base_path=tmp_path, binary=False,
                      path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')


@pytest.fixture
def buffered_file_storage_action_text(tmp_path) -> BufferedFileStorage:
    return BufferedFileStorage(base_path=tmp_path, binary=False, path='Encoded/{msg.sender}_{msg.name}.{msg.name}')


@pytest.fixture
def json_one_encoded() -> str:
    return '{"jsonrpc": "2.0", "id": 0, "method": "test", "params": ["abcd"]}'


@pytest.fixture
def file_containing_json(tmpdir, json_one_encoded) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("json"))
    p.write_text(json_one_encoded)
    return p


@pytest.fixture
def file_containing_multi_json(tmpdir, json_buffer) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("json"))
    p.write_text(json_buffer)
    return p


@pytest.fixture
def json_buffer() -> str:
    return '{"jsonrpc": "2.0", "id": 0, "method": "test", "params": ["abcd"]}{"jsonrpc": "2.0", "id": 1, "method": "test", "params": ["efgh"]}'


@pytest.fixture
def json_encoded_multi() -> List[str]:
    return [
        '{"jsonrpc": "2.0", "id": 0, "method": "test", "params": ["abcd"]}',
        '{"jsonrpc": "2.0", "id": 1, "method": "test", "params": ["efgh"]}'
    ]


@pytest.fixture
def invalid_json(json_encoded_multi) -> str:
    return '{"jsonrpc: "2.0", "id": 0, "method": "test", "params": ["abcd"]}'


@pytest.fixture
def json_decoded_multi() -> List[dict]:
    return [
        {'jsonrpc': "2.0", 'id': 0, 'method': 'test', 'params': ['abcd']},
        {'jsonrpc': "2.0", 'id': 1, 'method': 'test', 'params': ['efgh']}
    ]


@pytest.fixture
def json_rpc_request() -> dict:
    return {'jsonrpc': "2.0", 'id': 0, 'method': 'test', 'params': ['abcd']}


@pytest.fixture
def json_object(json_one_encoded, json_rpc_request, timestamp) -> JSONObject:
    return JSONObject(json_one_encoded, json_rpc_request, context=context, received_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, timestamp) -> List[JSONObject]:
    return [JSONObject(encoded, json_decoded_multi[i], context=context,
                       received_timestamp=timestamp) for i, encoded in
            enumerate(json_encoded_multi)]


@pytest.fixture
def json_rpc_result() -> dict:
    return {'jsonrpc': "2.0", 'id': 0, 'result': "Successfully processed abcd"}


@pytest.fixture
def json_rpc_notification_encoded() -> str:
    return '{"jsonrpc": "2.0", "method": "test", "params": ["abcd"]}'


@pytest.fixture
def json_rpc_notification() -> dict:
    return {'jsonrpc': "2.0", 'method': 'test', 'params': ['abcd']}


@pytest.fixture
def json_rpc_notification_object(json_rpc_notification_encoded, json_rpc_notification, timestamp) -> JSONObject:
    return JSONObject(json_one_encoded, json_rpc_notification, context=context,
                      received_timestamp=timestamp)


@pytest.fixture
def json_rpc_error_request(request) -> dict:
    if request.param == 'no_version':
        return {'id': 0, 'method': 'help', 'params': ['abcd']}
    if request.param == 'wrong_method':
        return {'jsonrpc': "2.0", 'id': 0, 'method': 'help', 'params': ['1']}
    if request.param == 'invalid_params':
        return {'jsonrpc': "2.0", 'id': 0, 'method': 'test', 'params': {'a': 2}}


@pytest.fixture
def json_rpc_error_response(request) -> dict:
    if request.param == 'no_version':
        return {"jsonrpc":  "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 0}
    if request.param == 'wrong_method':
        return {"jsonrpc":  "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 0}
    if request.param == 'invalid_params':
        return {"jsonrpc":  "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 0}


@pytest.fixture
def json_rpc_parse_error_response() -> dict:
    return {'jsonrpc': "2.0", 'error':{"code": -32700, "message": "Parse error"}}


@pytest.fixture
def json_rpc_invalid_params_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 0, 'error': {"code": -32600, "message": "Invalid Request"}}


@pytest.fixture
async def task_scheduler() -> TaskScheduler:
    scheduler = TaskScheduler()
    yield scheduler
    await scheduler.close(timeout=1)


@pytest.fixture
def deque() -> collections.deque:
    return collections.deque()


@pytest.fixture
def peername() -> Tuple[str, int]:
    return '127.0.0.1', 8888


@pytest.fixture
def peer_str() -> str:
    return '127.0.0.1:8888'


@pytest.fixture
def sock() -> Tuple[str, int]:
    return '127.0.0.1', 60000


@pytest.fixture
def extra(peername, sock) -> dict:
    return {'peername': peername, 'sockname': sock}


@pytest.fixture
async def tcp_transport(deque, extra) -> asyncio.Transport:
    yield MockTCPTransport(deque, extra=extra)


@pytest.fixture
async def udp_transport(deque, extra) -> asyncio.DatagramTransport:
    yield MockDatagramTransport(deque, extra=extra)


@pytest.fixture
async def tcp_server_protocol_one_way(buffered_file_storage_action_binary) -> TCPOneWayServerProtocol:
    yield TCPOneWayServerProtocol(dataformat=TCAPMAPASNObject, action=buffered_file_storage_action_binary, timeout=0.5)()


@pytest.fixture
async def tcp_server_protocol_two_way_no_response(buffered_file_storage_action_binary) -> TCPServerProtocol:
    yield TCPServerProtocol(dataformat=TCAPMAPASNObject, action=file_storage_action_binary, timeout=0.5)()


@pytest.fixture
async def tcp_server_protocol_two_way(json_rpc_action) -> TCPServerProtocol:
    yield TCPServerProtocol(dataformat=JSONObject, action=json_rpc_action, timeout=0.5)()


@pytest.fixture
async def tcp_client_protocol_one_way(json_rpc_requester) -> TCPClientProtocol:
    yield TCPClientProtocol(dataformat=TCAPMAPASNObject, requester=json_rpc_requester, timeout=0.5)()


@pytest.fixture
async def tcp_server_protocol_one_way_connected(tcp_server_protocol_one_way, tcp_transport) -> TCPOneWayServerProtocol:
    tcp_server_protocol_one_way.connection_made(tcp_transport)
    yield tcp_server_protocol_one_way
    if not tcp_transport.is_closing():
        tcp_server_protocol_one_way.connection_lost(None)


@pytest.fixture
async def tcp_two_way_server_protocol_no_response_connected(tcp_server_protocol_two_way_no_response, tcp_transport) -> TCPOneWayServerProtocol:
    tcp_server_protocol_two_way_no_response.connection_made(tcp_transport)
    yield tcp_server_protocol_two_way_no_response
    tcp_server_protocol_two_way_no_response.connection_lost(None)


@pytest.fixture
async def tcp_server_protocol_two_way_connected(tcp_server_protocol_two_way, tcp_transport) -> TCPOneWayServerProtocol:
    tcp_server_protocol_two_way.connection_made(tcp_transport)
    yield tcp_server_protocol_two_way
    tcp_server_protocol_two_way.connection_lost(None)


@pytest.fixture
async def tcp_client_protocol_connected(tcp_client_protocol, tcp_transport) -> TCPOneWayServerProtocol:
    tcp_client_protocol.connection_made(tcp_transport)
    yield tcp_client_protocol
    tcp_client_protocol.connection_lost(None)
