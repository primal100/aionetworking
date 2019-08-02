from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import collections
import pytest
import binascii
from pycrate_asn1dir.TCAP_MAP import TCAP_MAP_Messages
from pathlib import Path

from lib.actions.file_storage import FileStorage, BufferedFileStorage, ManagedFile
from lib.actions.jsonrpc import JSONRPCServer
from lib.actions.contrib.jsonrpc_crud import SampleJSONRPCServer
from lib.requesters.jsonrpc import SampleJSONRPCClient
from lib.conf.types import ConnectionLoggerType, LoggerType
from lib.conf.logging import ConnectionLogger, Logger
from lib.formats.contrib.json import JSONObject, JSONCodec
from lib.formats.contrib.types import JSONObjectType
from lib.formats.contrib.TCAP_MAP import TCAPMAPASNObject
from lib.formats.contrib.asn1 import PyCrateAsnCodec
from lib.formats.base import BufferObject
from lib.networking.adaptors import OneWayReceiverAdaptor, ReceiverAdaptor, SenderAdaptor
from lib.networking.network_connections import ConnectionsManager
from lib.networking.types import SimpleNetworkConnectionType
from lib.wrappers.counters import Counters, Counter
from lib.wrappers.schedulers import TaskScheduler

from tests.mock import MockTCPTransport, MockDatagramTransport

from typing import Dict, Any, List, Tuple, Union, Callable, AsyncGenerator


@pytest.fixture
def response(request):
    if request.param:                               #3.8 assignment expression
        return request.getfixturevalue(request.param)
    return request.param


@pytest.fixture
def notification(request):
    if request.param:                               #3.8 assignment expression
        return request.getfixturevalue(request.param)
    return request.param


@pytest.fixture
def items(request):
    if request.param:                               #3.8 assignment expression
        return request.getfixturevalue(request.param)
    return request.param


@pytest.fixture
def context() -> Dict[str, Any]:
    return {'protocol_name': 'TCP Server', 'alias': '127.0.0.1', 'host': '127.0.0.1', 'port': 8888,
            'peer': '127.0.0.1:8888', 'sock': '127.0.0.1:60000'}


@pytest.fixture
def receiver_logger() -> Logger:
    return Logger('receiver')


@pytest.fixture
def receiver_connection_logger(receiver_logger, context) -> ConnectionLogger:
    return receiver_logger.get_connection_logger(is_receiver=True, extra=context)


@pytest.fixture
def sender_logger() -> Logger:
    return Logger('sender')


@pytest.fixture
def sender_connection_logger(sender_logger, context) -> ConnectionLogger:
    return sender_logger.get_connection_logger(is_receiver=False, extra=context)


@pytest.fixture
def asn_codec(context) -> PyCrateAsnCodec:
    return PyCrateAsnCodec(TCAPMAPASNObject, context=context,
                           asn_class=TCAPMAPASNObject.asn_class)


@pytest.fixture
def asn_buffer() -> bytes:
    return b"bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0e\x81\xa4H\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00lj\xa2h\x02\x01\x010c\x02\x018\xa3^\xa1\\0Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12e\x16H\x04\xa5\x05\x00\x01I\x04\x84\x00\x01\xffl\x08\xa1\x06\x02\x01\x02\x02\x018d<I\x04W\x18\x00\x00k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x05\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x08\xa3\x06\x02\x01\x01\x02\x01\x0b"


@pytest.fixture
def asn_encoded_hex() -> Tuple[bytes, bytes, bytes, bytes]:
    return (
        b'62474804000000016b1e281c060700118605010101a011600f80020780a1090607040000010014026c1fa11d0201ff02012d30158007911497427533f38101008207911497797908f0',
        b'6581a44804840001ff4904a50500016b2a2828060700118605010101a01d611b80020780a109060704000001000e03a203020100a305a1030201006c6aa2680201013063020138a35ea15c305a04104b9d6191107536658cfe59880cd2ac2704104b8c43a2542050120467f333c00f42d804108c43a2542050120467f333c00f42d84b041043a2542050120467f333c00f42d84b8c0410a2551a058cdb00004b8d79f7caff5012',
        b'65164804a50500014904840001ff6c08a106020102020138',
        b'643c4904571800006b2a2828060700118605010101a01d611b80020780a109060704000001000503a203020100a305a1030201006c08a30602010102010b'
    )


@pytest.fixture
def asn_encoded_multi(asn_encoded_hex) -> List[bytes]:
    return [binascii.unhexlify(h) for h in asn_encoded_hex]


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
def asn_object(asn_one_encoded, asn_one_decoded, context) -> TCAPMAPASNObject:
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
def json_codec_no_context() -> JSONCodec:
    return JSONCodec(JSONObject, context={})


@pytest.fixture
def json_codec(context) -> JSONCodec:
    return JSONCodec(JSONObject, context=context)


@pytest.fixture
def default_notes(user1) -> Dict:
    return {0: {'id': 0, 'name': '1stnote', 'text': 'Hello, World!', 'user': user1[0]}}


@pytest.fixture
def after_create_notes(user1, default_notes) -> Dict:
    notes = default_notes.copy()
    notes.update({1: {'id': 1, 'name': 'Hello', 'text': 'This is my second note', 'user': user1[0]}})
    return notes


@pytest.fixture
def after_update_notes(user1) -> Dict:
    return {0: {'id': 0, 'name': '1stnote', 'text': 'Updating my first note', 'user': user1[0]}}


@pytest.fixture
def json_rpc_app(user1, user2, default_notes) -> SampleJSONRPCServer:
    app = SampleJSONRPCServer(notes=default_notes.copy())
    app.add_user(*user1)
    app.add_user(*user2)
    return app


@pytest.fixture
async def json_rpc_action(json_rpc_app) -> JSONRPCServer:
    action = JSONRPCServer(app=json_rpc_app, timeout=15)
    yield action
    await action.close()


@pytest.fixture
async def json_rpc_action_no_process_queue(json_rpc_app) -> JSONRPCServer:
    action = JSONRPCServer(app=json_rpc_app, timeout=3, start_task=False)
    yield action
    await asyncio.wait_for(action.close(), timeout=1)


@pytest.fixture
def json_rpc_requester() -> SampleJSONRPCClient:
    return SampleJSONRPCClient()


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
def buffered_file_storage_pre_action_binary(tmp_path) -> BufferedFileStorage:
    return BufferedFileStorage(base_path=tmp_path, binary=True, attr='record', path='{msg.sender}.recording')


@pytest.fixture
def buffered_file_storage_pre_action_text(tmp_path) -> BufferedFileStorage:
    return BufferedFileStorage(base_path=tmp_path, binary=True, attr='record', path='{msg.sender}.recording')


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
def user1() -> List[str, str]:
    return ['user1', 'password']


@pytest.fixture
def user2() -> List[str, str]:
    return ['user2', 'password']


@pytest.fixture
def user1_context(context, user1) -> Dict:
    c = context.copy()
    c['user'] = user1[0]
    return c


@pytest.fixture
def user2_context(context, user2) -> Dict:
    c = context.copy()
    c['user'] = user2[1]
    return c


@pytest.fixture
def user1_codec(json_codec, user1) -> JSONCodec:
    json_codec.context['user'] = user1[0]
    return json_codec


@pytest.fixture
def user2_codec(json_codec, user2) -> JSONCodec:
    json_codec.context['user'] = user2[0]
    return json_codec


@pytest.fixture
def json_rpc_login_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1}


@pytest.fixture
def json_rpc_login_request_encoded(user1) -> str:
    return '{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'


@pytest.fixture
def json_rpc_login_request_object(json_rpc_login_request, json_codec, timestamp) -> JSONObject:
    return json_codec.from_decoded(json_rpc_login_request, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_response_encoded(user1) -> str:
    return '{"jsonrpc": "2.0", "id": 1, "result": {"user": "user1", "message": "Login successful"}}'


@pytest.fixture
def json_buffer() -> str:
    return '{"jsonrpc": "2.0", "id": 1, "result": {"user": "user1", "message": "Login successful"}}{"jsonrpc": "2.0", "id": 1, "method": "logout"}'


@pytest.fixture
def json_rpc_login_response(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'user': user1[0], 'message': 'Login successful'}}


@pytest.fixture
def json_rpc_login_response_object(json_rpc_login_response, user1_codec, timestamp) -> JSONObject:
    return user1_codec.from_decoded(json_rpc_login_response, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_request_user2(user2) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1}


@pytest.fixture
def json_rpc_login_request_object_user2(json_rpc_login_request_user2, json_codec, timestamp) -> JSONObject:
    return json_codec.from_decoded(json_rpc_login_request_user2, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_response_user2(user2) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'user': user2[0], 'message': 'Login successful'}}


@pytest.fixture
def json_rpc_login_response_object_user2(json_rpc_login_response_user2, user2_codec, timestamp) -> JSONObject:
    return user2_codec.from_decoded(json_rpc_login_response_user2, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_logout_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 2, 'method': 'logout'}


@pytest.fixture
def json_rpc_logout_request_object(json_rpc_logout_request, json_codec, timestamp) -> JSONObject:
    return json_codec.from_decoded(json_rpc_logout_request, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_logout_request_encoded(user1) -> str:
    return '{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def json_rpc_logout_response(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 2, 'result': {'user': user1[0], 'message': 'Logout successful'}}


@pytest.fixture
def json_rpc_create_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'create', 'params': ('Hello', 'This is my second note')}


@pytest.fixture
def json_rpc_create_response(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'id': 1, 'user': user1[0], 'message': 'New note has been created'}}


@pytest.fixture
def json_rpc_notification_result() -> Dict:
    return {'id': 1, 'message': 'New note has been created', 'user': 'user1'}


@pytest.fixture
def json_rpc_create_notification(user1, json_rpc_notification_result) -> Dict:
    return {'jsonrpc': "2.0", 'result': json_rpc_notification_result}


@pytest.fixture
def json_rpc_create_notification_object(json_codec, json_rpc_create_notification_encoded) -> JSONObjectType:
    return next(json_codec.decode_buffer(json_rpc_create_notification_encoded))


@pytest.fixture
def json_rpc_create_notification_encoded() -> str:
    return '{"jsonrpc": "2.0", "result": {"id": 1, "message": "New note has been created", "user": "user1"}}'


@pytest.fixture
def json_rpc_update_notification(user1) -> Dict:
    return {'jsonrpc': "2.0", 'result': {'id': 0, 'message': 'Note has been updated', 'user': 'user1'}}


@pytest.fixture
def json_rpc_delete_notification(user1) -> Dict:
    return {'jsonrpc': "2.0", 'result': {'id': 0, 'message': 'Note has been deleted', 'user': 'user1'}}


@pytest.fixture
def json_rpc_update_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'update', 'params': {'id': 0, 'text': 'Updating my first note'}}


@pytest.fixture
def json_rpc_update_response(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'id': 0, 'user': user1[0], 'message': 'Note has been updated'}}


@pytest.fixture
def json_rpc_delete_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'delete', 'params': (0,)}


@pytest.fixture
def json_rpc_delete_response(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'id': 0, 'user': user1[0], 'message': 'Note has been deleted'}}


@pytest.fixture
def json_rpc_get_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'get', 'params': (0,)}


@pytest.fixture
def json_rpc_get_response(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1,
            'result': {'id': 0, 'user': user1[0], 'name': '1stnote', 'text': 'Hello, World!'}}


@pytest.fixture
def json_rpc_get_request_no_object(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'get', 'params': (3,)}


@pytest.fixture
def json_rpc_subscribe_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'method': 'subscribe_to_user', 'params': [user1[0],]}


@pytest.fixture
def json_rpc_subscribe_request_object(json_rpc_subscribe_request, user2_codec, timestamp) -> JSONObject:
    return user2_codec.from_decoded(json_rpc_subscribe_request, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_unsubscribe_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'method': 'unsubscribe_from_user', 'params': (user1[0],)}


@pytest.fixture
def json_rpc_unsubscribe_request_object(json_rpc_unsubscribe_request, user2_codec, timestamp) -> JSONObject:
    return user2_codec.from_decoded(json_rpc_unsubscribe_request, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_wrong_password(user1) -> dict:
    user = user1[0], 'abcd1234'
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user}


@pytest.fixture
def json_rpc_login_wrong_user_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'code': -30000, 'message': 'Login failed'}}


@pytest.fixture
def json_rpc_login_wrong_user_response() -> dict:
    user = ('user3', 'abcd1234')
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user}


@pytest.fixture
def json_rpc_invalid_login_request_object(json_rpc_login_invalid, user1_codec, timestamp) -> JSONObject:
    return user1_codec.from_decoded(json_rpc_login_invalid, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_invalid_login_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'code': -30000, 'message': 'Login failed'}}


@pytest.fixture
def json_rpc_invalid_login_response_object(json_rpc_invalid_login_response, user1_codec, timestamp) -> JSONObject:
    return user1_codec.from_decoded(json_rpc_invalid_login_response, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_wrong_method_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'creat', 'params': ('Hello', 'This is my second note')}


@pytest.fixture
def json_rpc_wrong_method_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'code': -30601, 'message': 'Method not found'}}


@pytest.fixture
def json_rpc_authorisation_error() -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {'code': -30601, 'message': 'Method not found'}}


@pytest.fixture
def json_rpc_invalid_params_request(user1) -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1[0]}


@pytest.fixture
def json_rpc_invalid_params_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {"code": -32602, "message": "Invalid params"}}


@pytest.fixture
def json_rpc_permissions_error_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 1, 'result': {"code": -30001, "message": "You do not have permissions to perform this action"}}


@pytest.fixture
def json_rpc_object_no_user(json_codec, request) -> JSONObjectType:
    if request.param:
        return json_codec.from_decoded(request.getfixturevalue(request.param), received_timestamp=timestamp)
    return request.param


@pytest.fixture
def subscribe_key() -> str:
    return "user_user1"


@pytest.fixture
def json_rpc_object_user1(user1_codec, request) -> JSONObjectType:
    return user1_codec.from_decoded(request.getfixturevalue(request.param), received_timestamp=timestamp)


@pytest.fixture
def json_rpc_object_user1_response(user1_codec, request) -> JSONObjectType:
    return user1_codec.from_decoded(request.getfixturevalue(request.param), received_timestamp=timestamp)


@pytest.fixture
def json_rpc_object_user(request, json_codec, json_rpc_object_no_user, json_rpc_object_user1, json_rpc_object_user1_response, timestamp):
    user, fixture = request.param
    json_object = json_codec.from_decoded(request.getfixturevalue(fixture, received_timestamp=timestamp))
    fixture['context']['user'] = user
    return fixture


@pytest.fixture
def json_rpc_object_user2(user2_codec, request):
    return user2_codec.from_decoded(request.getfixturevalue(request.param), received_timestamp=timestamp)


@pytest.fixture
def json_object(json_one_encoded, json_rpc_request, timestamp) -> JSONObject:
    return JSONObject(json_one_encoded, json_rpc_request, context=context, received_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, timestamp, context) -> List[JSONObject]:
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
        return {'id': 0, 'method': 'delete', 'params': (0,)}
    if request.param == 'wrong_method':
        return {'jsonrpc': "2.0", 'id': 0, 'method': 'help', 'params': ['1']}
    if request.param == 'invalid_params':
        return {'jsonrpc': "2.0", 'id': 0, 'method': 'delete', 'params': {'a': 2}}


@pytest.fixture
def json_rpc_error_response(request) -> dict:
    if request.param == 'no_version':
        return {"jsonrpc":  "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 0}
    if request.param == 'wrong_method':
        return {"jsonrpc":  "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 0}
    if request.param == 'invalid_params':
        return {"jsonrpc":  "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 0}


@pytest.fixture
def json_rpc_error_response_encoded(request) -> str:
    if request.param == 'no_version':
        return '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 0}'
    if request.param == 'wrong_method':
        return '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 0}'
    if request.param == 'invalid_params':
        return '{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 0}'

@pytest.fixture
def json_rpc_parse_error_response() -> dict:
    return {'jsonrpc': "2.0", 'error':{"code": -32700, "message": "Parse error"}}


@pytest.fixture
def json_rpc_parse_error_response_encoded() -> str:
    return '{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}'



@pytest.fixture
def json_rpc_invalid_params_response() -> dict:
    return {'jsonrpc': "2.0", 'id': 0, 'error': {"code": -32600, "message": "Invalid Request"}}


@pytest.fixture
async def task_scheduler() -> TaskScheduler:
    scheduler = TaskScheduler()
    yield scheduler
    await asyncio.wait_for(scheduler.close(), timeout=1)


@pytest.fixture
def deque() -> collections.deque:
    return collections.deque()


@pytest.fixture
async def queue() -> asyncio.Queue:
    yield asyncio.Queue()


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
async def counter() -> Counter:
    yield Counter()


@pytest.fixture
async def counters() -> Counters:
    yield Counters()


@pytest.fixture
async def future():
    yield asyncio.Future()


@pytest.fixture
def wait_get_double_coro() -> Callable:
    async def wait_get_double(delay: Union[int, float], num: int):
        await asyncio.sleep(delay)
        if num > 4:
            raise ValueError()
        return num * 2
    return wait_get_double


@pytest.fixture
def success() -> Callable:
    def success_func(res: Any, fut: asyncio.Future):
        fut.set_result(res)
    return success_func


@pytest.fixture
def fail() -> Callable:
    def fail_func(exc: BaseException, fut: asyncio.Future):
        fut.set_exception(exc)
    return fail_func


@pytest.fixture
def connections_manager() -> ConnectionsManager:
    from lib.networking.network_connections import connections_manager
    yield connections_manager
    connections_manager.clear()


@dataclass
class SimpleNetworkConnection:
    peer_str: str
    parent: int
    deque: collections.deque

    def encode_and_send_msg(self, msg_decoded: Any) -> None:
        self.deque.append(msg_decoded)


@pytest.fixture
def simple_network_connections(deque, peer_str) -> List[SimpleNetworkConnection]:
    return [SimpleNetworkConnection(peer_str, 1, deque), SimpleNetworkConnection('127.0.0.1:4444', 1, deque)]


@pytest.fixture
def simple_network_connection(simple_network_connections) -> SimpleNetworkConnection:
    return simple_network_connections[0]


@pytest.fixture
def connections_manager_with_connection(connections_manager, simple_network_connection) -> ConnectionsManager:
    connections_manager.add_connection(simple_network_connection)
    return connections_manager


@pytest.fixture
def buffer_asn1_1(asn_encoded_multi) -> bytes:
    half_buffer = asn_encoded_multi[0:2]
    return b''.join(half_buffer)


@pytest.fixture
def buffer_asn1_2(asn_encoded_multi) -> bytes:
    half_buffer = asn_encoded_multi[2:4]
    return b''.join(half_buffer)


@pytest.fixture
def buffer_object_asn1(buffer_asn1_1, timestamp, context) -> BufferObject:
    return BufferObject(buffer_asn1_1, received_timestamp=timestamp, context=context)


@pytest.fixture
def buffer_object_asn2(buffer_asn1_2, timestamp, context) -> BufferObject:
    return BufferObject(buffer_asn1_2, received_timestamp=timestamp + timedelta(seconds=1), context=context)


@pytest.fixture
def buffer_json_1(json_encoded_multi) -> str:
    return json_encoded_multi[0]


@pytest.fixture
def buffer_json_2(json_encoded_multi) -> str:
    return json_encoded_multi[1]


@pytest.fixture
def asn1_recording() -> bytes:
    return b"\x00\x00\x00\x00\x00\x01\t\x00\x00\x00127.0.0.1\xf0\x00\x00\x00bGH\x04\x00\x00\x00\x01k\x1e(\x1c\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x11`\x0f\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x14\x02l\x1f\xa1\x1d\x02\x01\xff\x02\x01-0\x15\x80\x07\x91\x14\x97Bu3\xf3\x81\x01\x00\x82\x07\x91\x14\x97yy\x08\xf0e\x81\xa4H\x04\x84\x00\x01\xffI\x04\xa5\x05\x00\x01k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x0e\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00lj\xa2h\x02\x01\x010c\x02\x018\xa3^\xa1\\0Z\x04\x10K\x9da\x91\x10u6e\x8c\xfeY\x88\x0c\xd2\xac'\x04\x10K\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8\x04\x10\x8cC\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x04\x10C\xa2T P\x12\x04g\xf33\xc0\x0fB\xd8K\x8c\x04\x10\xa2U\x1a\x05\x8c\xdb\x00\x00K\x8dy\xf7\xca\xffP\x12\x00\x00\x00\x80?\x01\t\x00\x00\x00127.0.0.1V\x00\x00\x00e\x16H\x04\xa5\x05\x00\x01I\x04\x84\x00\x01\xffl\x08\xa1\x06\x02\x01\x02\x02\x018d<I\x04W\x18\x00\x00k*((\x06\x07\x00\x11\x86\x05\x01\x01\x01\xa0\x1da\x1b\x80\x02\x07\x80\xa1\t\x06\x07\x04\x00\x00\x01\x00\x05\x03\xa2\x03\x02\x01\x00\xa3\x05\xa1\x03\x02\x01\x00l\x08\xa3\x06\x02\x01\x01\x02\x01\x0b"


@pytest.fixture
def file_containing_asn1_recording(tmpdir, asn1_recording) -> Path:
    p = Path(tmpdir.mkdir("recording").join("asn1.recording"))
    p.write_bytes(asn1_recording)
    return p


@pytest.fixture
def asn1_recording_data(buffer_asn1_1, buffer_asn1_2) -> List[Dict]:
    return [{
        'sent_by_server': False,
        'seconds': 0.0,
        'peer': "127.0.0.1",
        'data': buffer_asn1_1
    },
    {
        'sent_by_server': False,
        'seconds': 1.0,
        'peer': "127.0.0.1",
        'data': buffer_asn1_2
    }
    ]


@pytest.fixture
def json_recording() -> bytes:
    return b'\x00\x00\x00\x00\x00\x00\t\x00\x00\x00127.0.0.1O\x00\x00\x00{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}\x00\x00\x00\x80?\x00\t\x00\x00\x00127.0.0.1/\x00\x00\x00{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def buffer_object_json1(buffer_json_1, timestamp, context) -> BufferObject:
    return BufferObject(buffer_json_1, received_timestamp=timestamp, context=context)


@pytest.fixture
def buffer_object_json2(buffer_json_2, timestamp, context) -> BufferObject:
    return BufferObject(buffer_json_2, received_timestamp=timestamp + timedelta(seconds=1), context=context)


@pytest.fixture
def json_recording_data(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[Dict]:
    return [{
        'sent_by_server': False,
        'seconds': 0.0,
        'peer': "127.0.0.1",
        'data': json_rpc_login_request_encoded
    },
    {
        'sent_by_server': False,
        'seconds': 1.0,
        'peer': "127.0.0.1",
        'data': json_rpc_logout_request_encoded
    }
    ]


@pytest.fixture
def one_way_receiver_adaptor(buffered_file_storage_action_binary, buffered_file_storage_pre_action_binary, context,
                             receiver_connection_logger) -> OneWayReceiverAdaptor:
    return OneWayReceiverAdaptor(TCAPMAPASNObject, action=buffered_file_storage_action_binary,
                                 context=context, logger=receiver_connection_logger,
                                 preaction=buffered_file_storage_pre_action_binary)


@pytest.fixture
async def one_way_sender_adaptor(context, sender_connection_logger, deque) -> SenderAdaptor:
    yield SenderAdaptor(TCAPMAPASNObject, context=context, logger=sender_connection_logger, send=deque.append)


@pytest.fixture
def two_way_receiver_adaptor(json_rpc_action, buffered_file_storage_pre_action_binary, context,
                             receiver_connection_logger, deque) -> ReceiverAdaptor:
    return ReceiverAdaptor(JSONObject, action=json_rpc_action,
                           context=context, logger=receiver_connection_logger,
                           preaction=buffered_file_storage_pre_action_binary, send=deque.append)


@pytest.fixture
async def two_way_sender_adaptor(context, sender_connection_logger, json_rpc_requester, queue) -> SenderAdaptor:
    yield SenderAdaptor(JSONObject, context=context, logger=sender_connection_logger, requester=json_rpc_requester, send=queue.put_nowait)


"""
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
"""