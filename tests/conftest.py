from datetime import datetime
import pytest
import binascii
from pycrate_asn1dir.TCAP_MAP import TCAP_MAP_Messages
from pathlib import Path

from lib.actions.file_storage import FileStorage, BufferedFileStorage
from lib.actions.jsonrpc import SampleJSONRPCServer
from lib.formats.contrib.json import JSONObject, JSONCodec
from lib.formats.contrib.TCAP_MAP import TCAPMAPASNObject
from lib.formats.contrib.asn1 import PyCrateAsnCodec


@pytest.fixture
def asn_codec():
    return PyCrateAsnCodec(TCAPMAPASNObject, context={'sender': '127.0.0.1'},
                        asn_class=TCAPMAPASNObject.asn_class)


@pytest.fixture
def asn_buffer():
    return b"bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0e\x81\xaaH\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x80\xa2l\x02\x01\x010g\x02\x018\xa3\x80\xa1\x800Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x00\x00\x00e\x16H\x04\xa5\x05\x00\x01I\x04\x84\x00\x01\xffl\x08\xa1\x06\x02\x01\x02\x02\x018d<I\x04W\x18\x00\x00k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x05\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x08\xa3\x06\x02\x01\x01\x02\x01\x0b"


@pytest.fixture
def asn_encoded_multi():
    hexes = (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581aa4804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c80a26c0201013067020138a380a180305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012000000000000',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )
    return [binascii.unhexlify(h) for h in hexes]


@pytest.fixture
def asn_decoded_multi(asn_encoded_multi):
    decoder = TCAP_MAP_Messages.TCAP_MAP_Message
    decoded = []
    for encoded in asn_encoded_multi:
        decoder.from_ber(encoded)
        decoded.append(decoder())
    return decoded


@pytest.fixture
def timestamp():
    return datetime(2019, 1, 1, 1, 1)


@pytest.fixture
def asn_objects(asn_encoded_multi, asn_decoded_multi, timestamp):
    return [TCAPMAPASNObject(encoded, asn_decoded_multi[i], context={'sender': '127.0.0.1'},
                            received_timestamp=timestamp) for i, encoded in
           enumerate(asn_encoded_multi)]


@pytest.fixture
def asn_one_encoded():
    return b'bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0'


@pytest.fixture
def asn_one_decoded():
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
def asn_object(asn_one_encoded, asn_one_decoded):
    return TCAPMAPASNObject(asn_one_encoded, asn_one_decoded, context={'sender': '127.0.0.1'},
                           received_timestamp=datetime(2019, 1, 1, 1, 1))


@pytest.fixture
def file_containing_asn(tmpdir, asn_one_encoded):
    p = Path(tmpdir.mkdir("encoded").join("testasn"))
    p.write_bytes(asn_one_encoded)
    return p


@pytest.fixture
def json_codec():
    return JSONCodec(JSONObject, context={'sender': '127.0.0.1'})


@pytest.fixture
def json_rpc_action():
    return SampleJSONRPCServer(timeout=3)


@pytest.fixture
def managed_file_path(tmp_path):
    return tmp_path/'managed_file1'


@pytest.fixture
def file_storage_action(tmp_path):
    return FileStorage(base_path=tmp_path,
                      path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')


@pytest.fixture
def buffered_file_storage_action(tmp_path):
    return BufferedFileStorage(base_path=tmp_path, path='Encoded/{msg.name}')


@pytest.fixture
def json_one_encoded():
    return '{"jsonrpc": 2.0, "id": 0, "method": "test", "params": ["abcd"]}'


@pytest.fixture
def file_containing_json(tmpdir, json_one_encoded):
    p = Path(tmpdir.mkdir("encoded").join("json"))
    p.write_text(json_one_encoded)
    return p


@pytest.fixture
def json_buffer():
    return '{"jsonrpc": 2.0, "id": 0, "method": "test", "params": ["abcd"]}{"jsonrpc": 2.0, "id": 1, "method": "test", "params": ["efgh"]}'


@pytest.fixture
def json_encoded_multi():
    return [
        '{"jsonrpc": 2.0, "id": 0, "method": "test", "params": ["abcd"]}',
        '{"jsonrpc": 2.0, "id": 1, "method": "test", "params": ["efgh"]}'
    ]


@pytest.fixture
def json_decoded_multi():
    return [
        {'jsonrpc': 2.0, 'id': 0, 'method': 'test', 'params': ['abcd']},
        {'jsonrpc': 2.0, 'id': 1, 'method': 'test', 'params': ['efgh']}
    ]


@pytest.fixture
def json_rpc_request():
    return {'jsonrpc': 2.0, 'id': 0, 'method': 'test', 'params': ['abcd']}


@pytest.fixture
def json_object(json_one_encoded, json_rpc_request, timestamp):
    return JSONObject(json_one_encoded, json_rpc_request, context={'sender': '127.0.0.1'}, received_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, timestamp):
    return [JSONObject(encoded, json_decoded_multi[i], context={'sender': '127.0.0.1'},
                            received_timestamp=timestamp) for i, encoded in
           enumerate(json_encoded_multi)]


@pytest.fixture
def json_rpc_result():
    return {'jsonrpc': 2.0, 'id': 0, 'result': "Successfully processed abcd"}


@pytest.fixture
def json_rpc_notification():
    return {'jsonrpc': 2.0, 'method': 'test', 'params': ['abcd']}


@pytest.fixture
def json_rpc_no_version():
    return {'id': 0, 'method': 'help', 'params': ['abcd']}


@pytest.fixture
def json_rpc_wrong_method():
    return {'jsonrpc': 2.0, 'id': 0, 'method': 'help', 'params': ['1']}


@pytest.fixture
def json_rpc_invalid_params():
    return {'jsonrpc': 2.0, 'method': 'test', 'params': {'a': 2}}


@pytest.fixture
def json_rpc_parse_error_response():
    return {'jsonrpc': 2.0, 'error':{"code": -32700, "message": "Parse error"}}


@pytest.fixture
def json_rpc_invalid_params_response():
    return {'jsonrpc': 2.0, 'id': 0, 'error': {"code": -32600, "message": "Invalid Request"}}
