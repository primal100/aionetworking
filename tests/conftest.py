from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import collections
import pytest
import logging
import os
from pathlib import Path

from aionetworking.actions import FileStorage, BufferedFileStorage
from aionetworking.logging import ConnectionLoggerStats
from aionetworking.formats.contrib import JSONObject, JSONCodec
from aionetworking.formats.contrib import PickleCodec, PickleObject
from aionetworking.types.formats import JSONObjectType
from aionetworking.formats import BufferObject
from aionetworking.networking import ReceiverAdaptor, SenderAdaptor
from aionetworking.networking import BaseConnectionProtocol, TCPServerConnection, TCPClientConnection

from aionetworking.types.networking import SimpleNetworkConnectionType
from aionetworking.networking.protocol_factories import StreamServerProtocolFactory
from aionetworking.networking.connections_manager import ConnectionsManager
from aionetworking.receivers.base import BaseServer
from aionetworking.receivers.servers import pipe_server
from aionetworking.senders.base import BaseClient
from aionetworking.senders.clients import pipe_client
from aionetworking.utils import set_loop_policy

from typing import Dict, Any, List, Tuple, Union, Callable, Optional, Type


def pytest_addoption(parser):
    default = 'proactor' if os.name == 'nt' else 'selector'
    choices = ('selector', 'uvloop') if os.name == 'linux' else ('proactor', 'selector')
    parser.addoption(
        "--loop",
        action="store",
        default=default,
        help=f"Loop to use. Choices are: {','.join(choices)}",
    )


def pytest_configure(config):
    loop_type = config.getoption("--loop")
    if loop_type:
        set_loop_policy(linux_loop_type=loop_type, windows_loop_type=loop_type)


def get_fixture(request, param=None):
    if not param:
        param = request.param
    return request.getfixturevalue(param.__name__)


def get_fixtures(request):
    return [request.getfixturevalue(param.__name__) for param in request.param]


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2019, 1, 1, 1, 1)


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
def context_client() -> Dict[str, Any]:
    return {'protocol_name': 'TCP Client', 'host': '127.0.0.1', 'port': 8888,
            'peer': '127.0.0.1:8888', 'sock': '127.0.0.1:60000', 'alias': '127.0.0.1', 'server': '127.0.0.1:8888',
            'client': '127.0.0.1:60000'}


@pytest.fixture
def logger_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{asctime} - {relativeCreated} - {levelname} - {module} - {funcName} - {name} - {message}", style='{'
    )


@pytest.fixture
def connection_logger_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{asctime} - {relativeCreated} - {levelname} - {taskname} - {module} - {funcName} - {name} - {peer} - {message}", style='{'
    )


@pytest.fixture
def raw_received_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{message}", style='{'
    )


@pytest.fixture
def logging_handler_cls() -> Type[logging.Handler]:
    return logging.StreamHandler


@pytest.fixture
def receiver_logging_handler(logging_handler_cls, logger_formatter) -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(logger_formatter)
    return handler


@pytest.fixture
def connection_logging_handler(logging_handler_cls, connection_logger_formatter) -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(connection_logger_formatter)
    return handler


@pytest.fixture
def stats_logging_handler(logging_handler_cls, stats_formatter) -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(stats_formatter)
    return handler


@pytest.fixture
def raw_received_handler(logging_handler_cls, raw_received_formatter) -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(raw_received_formatter)
    return handler


@pytest.fixture
def log_buffers(raw_received_handler):
    logger = logging.getLogger('receiver.raw_received')
    logger.setLevel(logging.ERROR)
    logger.addHandler(raw_received_handler)
    yield
    logger.setLevel(logging.ERROR)


@pytest.fixture
def receiver_debug_logging_extended(receiver_logging_handler, connection_logging_handler, stats_logging_handler):
    default_level = logging.ERROR
    logger = logging.getLogger('receiver')
    logger.setLevel(default_level)
    logger.addHandler(receiver_logging_handler)
    logger = logging.getLogger('sender')
    logger.setLevel(default_level)
    logger.addHandler(receiver_logging_handler)
    actions_logger = logging.getLogger('receiver.actions')
    actions_logger.addHandler(receiver_logging_handler)
    actions_logger.setLevel(default_level)
    actions_logger.propagate = False
    sender_connection_logger = logging.getLogger('sender.connection')
    sender_connection_logger.addHandler(connection_logging_handler)
    sender_connection_logger.propagate = False
    sender_connection_logger.setLevel(logging.ERROR)
    connection_logger = logging.getLogger('receiver.connection')
    logging.getLogger('receiver.raw_received').setLevel(logging.ERROR)
    logging.getLogger('receiver.data_received').setLevel(logging.ERROR)
    logging.getLogger('sender.raw_received').setLevel(logging.ERROR)
    logging.getLogger('sender.data_received').setLevel(logging.ERROR)
    logging.getLogger('sender.raw_sent').setLevel(logging.ERROR)
    connection_logger.addHandler(connection_logging_handler)
    connection_logger.propagate = False
    connection_logger.setLevel(default_level)
    stats_logger = logging.getLogger('receiver.stats')
    stats_logger.addHandler(stats_logging_handler)
    stats_logger.setLevel(logging.ERROR)
    stats_logger.propagate = False
    asyncio.get_event_loop().set_debug(False)
    logger = logging.getLogger('asyncio')
    logger.addHandler(receiver_logging_handler)
    logger.setLevel(logging.ERROR)
    yield
    stats_logger.setLevel(logging.ERROR)


@pytest.fixture
def sender_connection_logger_stats(sender_connection_logger, context_client, caplog) -> ConnectionLoggerStats:
    caplog.set_level(logging.ERROR, "sender.stats")
    caplog.set_level(logging.ERROR, "sender.connection")
    yield sender_logger.get_connection_logger(extra=context_client)
    caplog.set_level(logging.ERROR, "sender.stats")
    caplog.set_level(logging.ERROR, "sender.connection")


@pytest.fixture
def pickle_codec(context, receiver_connection_logger) -> PickleCodec:
    return PickleCodec(PickleObject, context=context, logger=receiver_connection_logger)


@pytest.fixture
def json_codec_no_context() -> JSONCodec:
    return JSONCodec(JSONObject, context={})


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
def file_storage_action_binary(tmp_path) -> FileStorage:
    return FileStorage(base_path=tmp_path, binary=True,
                      path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')


@pytest.fixture
async def buffered_file_storage_action_binary(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=True, path='Encoded/{msg.sender}_{msg.name}.{msg.name}')
    yield action
    await action.close()


@pytest.fixture
async def buffered_file_storage_action_binary_pipe(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=True, path='Encoded/pipe.{msg.name}')
    yield action
    await action.close()


@pytest.fixture
async def buffered_file_storage_pre_action_binary_pipe(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=True, attr='recording', path='pipe.recording')
    yield action
    await action.close()


@pytest.fixture
async def buffered_file_storage_pre_action_binary(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=True, attr='recording', path='{msg.sender}.recording')
    yield action
    await action.close()


@pytest.fixture
async def buffered_file_storage_pre_action_text(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=True, attr='recording', path='{msg.sender}.recording')
    yield action
    await action.close()


@pytest.fixture
async def file_storage_action_text(tmp_path) -> FileStorage:
    action = FileStorage(base_path=tmp_path, binary=False,
                      path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')
    yield action
    await action.close()


@pytest.fixture
async def buffered_file_storage_action_text(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=False, path='Encoded/{msg.sender}_{msg.name}.{msg.name}')
    yield action
    await action.close()


@pytest.fixture
def file_containing_json(tmpdir, json_rpc_login_request_encoded) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("json"))
    p.write_text(json_rpc_login_request_encoded)
    return p


@pytest.fixture
def invalid_json(json_encoded_multi) -> str:
    return '{"jsonrpc: "2.0", "id": 0, "method": "test", "params": ["abcd"]}'


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
def json_rpc_login_request_object(json_rpc_login_request, json_codec, timestamp) -> JSONObject:
    return json_codec.from_decoded(json_rpc_login_request, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_response_encoded(user1) -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "result": {"user": "user1", "message": "Login successful"}}'


@pytest.fixture
def json_buffer() -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


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
def json_rpc_logout_request_object(json_rpc_logout_request, json_codec, timestamp) -> JSONObject:
    return json_codec.from_decoded(json_rpc_logout_request, received_timestamp=timestamp)


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
def json_rpc_notification_object(json_rpc_create_notification_encoded, json_rpc_create_notification, timestamp) -> JSONObject:
    return JSONObject(json_rpc_create_notification_encoded, json_rpc_create_notification, context=context,
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
def deque() -> collections.deque:
    return collections.deque()


@pytest.fixture
async def queue() -> asyncio.Queue:
    yield asyncio.Queue()


@pytest.fixture
def peer_str() -> str:
    return '127.0.0.1:60000'





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
def json_recording() -> bytes:
    return b'\x00\x00\x00\x00\x00\x00\t\x00\x00\x00127.0.0.1O\x00\x00\x00{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}\x00\x00\x00\x80?\x00\t\x00\x00\x00127.0.0.1/\x00\x00\x00{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def buffer_object_json1(buffer_json_1, timestamp, context) -> BufferObject:
    return BufferObject(buffer_json_1, received_timestamp=timestamp, context=context)


@pytest.fixture
def buffer_object_json2(buffer_json_2, timestamp, context) -> BufferObject:
    return BufferObject(buffer_json_2, received_timestamp=timestamp + timedelta(seconds=1), context=context)


@pytest.fixture
def protocol_factory_two_way_server(json_rpc_action, receiver_logger, buffered_file_storage_pre_action_binary) -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        action=json_rpc_action,
        preaction=buffered_file_storage_pre_action_binary,
        dataformat=JSONObject,
        logger=receiver_logger)
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory


@pytest.fixture
async def two_way_receiver_adaptor(echo_action, buffered_file_storage_pre_action_binary, context,
                                   receiver_connection_logger, queue) -> ReceiverAdaptor:
    yield ReceiverAdaptor(JSONObject, action=echo_action,
                          context=context, logger=receiver_connection_logger,
                          preaction=buffered_file_storage_pre_action_binary, send=queue.put_nowait)


@pytest.fixture
async def two_way_sender_adaptor(context_client, sender_connection_logger, json_rpc_requester, queue) -> SenderAdaptor:
    yield SenderAdaptor(JSONObject, context=context_client, logger=sender_connection_logger,
                        requester=json_rpc_requester, send=queue.put_nowait)


@pytest.fixture
async def tcp_protocol_one_way_server_benchmark(buffered_file_storage_action_binary,
                                                buffered_file_storage_pre_action_binary,
                                                receiver_logger) -> TCPServerConnection:
    yield TCPServerConnection(dataformat=TCAPMAPASNObject, action=buffered_file_storage_action_binary,
                                    parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp', logger=receiver_logger)


@pytest.fixture
async def tcp_protocol_one_way_pipe(buffered_file_storage_pre_action_binary_pipe,
                                    buffered_file_storage_action_binary_pipe,
                                    receiver_logger, pipe_path) -> TCPServerConnection:
    yield TCPServerConnection(dataformat=TCAPMAPASNObject, action=buffered_file_storage_action_binary_pipe,
                                    preaction=buffered_file_storage_pre_action_binary_pipe, peer_prefix='pipe',
                                    parent_name=f"Windows Named Pipe Server {pipe_path}", logger=receiver_logger)


@pytest.fixture
async def tcp_protocol_two_way_server(json_rpc_action, buffered_file_storage_pre_action_binary,
                                      receiver_logger) -> TCPServerConnection:
    yield TCPServerConnection(dataformat=JSONObject, action=json_rpc_action, peer_prefix='tcp',
                              parent_name="TCP Server 127.0.0.1:8888",
                              preaction=buffered_file_storage_pre_action_binary, logger=receiver_logger)


@pytest.fixture
async def tcp_protocol_two_way_client(json_rpc_requester, sender_logger) -> TCPClientConnection:
    yield TCPClientConnection(dataformat=JSONObject, logger=sender_logger, requester=json_rpc_requester,
                              parent_name="TCP Client 127.0.0.1:0", peer_prefix='tcp')







@pytest.fixture
def pipe_server_one_way(protocol_factory_one_way_server, receiver_logger, pipe_path):
    return pipe_server(protocol_factory=protocol_factory_one_way_server, logger=receiver_logger, path=pipe_path)


@pytest.fixture
def pipe_client_one_way(protocol_factory_one_way_client, sender_logger, pipe_path):
    return pipe_client(protocol_factory=protocol_factory_one_way_client, logger=sender_logger, path=pipe_path)


@pytest.fixture
def pipe_server_two_way(protocol_factory_two_way_server, receiver_logger, pipe_path) -> BaseServer:
    return pipe_server(protocol_factory=protocol_factory_two_way_server, logger=receiver_logger, path=pipe_path)


@pytest.fixture
def pipe_client_two_way(protocol_factory_two_way_client, sender_logger, pipe_path) -> BaseServer:
    return pipe_client(protocol_factory=protocol_factory_two_way_client, logger=sender_logger, path=pipe_path)


@pytest.fixture
def expected_server_context(request, server_client_args) -> Dict[str, Any]:
    return get_fixture(request, server_client_args[2])


@pytest.fixture
def expected_client_context(request, server_client_args) -> Dict[str, Any]:
    return get_fixture(request, server_client_args[3])


@pytest.fixture
def _client_sender(request, server_client_args) -> BaseClient:
    return get_fixture(request, server_client_args[1])


@pytest.fixture
async def client_sender(_client_sender, server_started) -> BaseClient:
    yield _client_sender
    if not _client_sender.is_closing():
        await _client_sender.close()


@pytest.fixture
async def client_connected(client_sender, server_started) -> Tuple[BaseClient, BaseConnectionProtocol]:
    async with client_sender as conn:
        yield client_sender, conn


@pytest.fixture
def recording_file_name(one_way_server_client_args) -> str:
    return one_way_server_client_args[2]


@pytest.fixture
def asn_file_name(one_way_server_client_args) -> str:
    return one_way_server_client_args[3]


@pytest.fixture
def server_connection_context(request, two_way_server_client_args):
    return get_fixture(request, two_way_server_client_args[2])


@pytest.fixture
def client_connection_context(request, two_way_server_client_args):
    return get_fixture(request, two_way_server_client_args[3])


@pytest.fixture
def _one_way_server_receiver(request, one_way_server_client_args) -> Optional[BaseServer]:
    return get_fixture(request, one_way_server_client_args[0])


@pytest.fixture
def _two_way_server_receiver(request, two_way_server_client_args) -> Optional[BaseServer]:
    return get_fixture(request, two_way_server_client_args[0])


@pytest.fixture
async def one_way_server_receiver(_one_way_server_receiver) -> BaseServer:
    yield _one_way_server_receiver
    if _one_way_server_receiver.is_started():
        await _one_way_server_receiver.close()


@pytest.fixture
async def two_way_server_receiver(_two_way_server_receiver) -> BaseServer:
    yield _two_way_server_receiver
    if _two_way_server_receiver.is_started():
        await _two_way_server_receiver.close()


"""@pytest.fixture
async def one_way_server_started(one_way_server_receiver) -> BaseServer:
    await one_way_server_receiver.start()
    yield one_way_server_receiver"""


@pytest.fixture
async def one_way_server_started_benchmark(tcp_server_one_way_benchmark) -> BaseServer:
    await tcp_server_one_way_benchmark.start()
    yield tcp_server_one_way_benchmark
    await tcp_server_one_way_benchmark.close()


@pytest.fixture
async def two_way_server_started(two_way_server_receiver) -> BaseServer:
    await two_way_server_receiver.start()
    yield two_way_server_receiver


@pytest.fixture
def _one_way_client_sender(request, one_way_server_client_args) -> BaseClient:
    return get_fixture(request, one_way_server_client_args[1])


@pytest.fixture
def _two_way_client_sender(request, two_way_server_client_args) -> BaseClient:
    return get_fixture(request, two_way_server_client_args[1])


@pytest.fixture
async def one_way_client_sender(_one_way_client_sender, one_way_server_started) -> BaseClient:
    yield _one_way_client_sender
    if not _one_way_client_sender.is_closing():
        await _one_way_client_sender.close()


@pytest.fixture
async def two_way_client_sender(_two_way_client_sender, one_way_server_started) -> BaseClient:
    yield _two_way_client_sender
    if not _two_way_client_sender.is_closing():
        await _two_way_client_sender.close()


@pytest.fixture
async def one_way_client_connected(one_way_client_sender, one_way_server_started) -> Tuple[
        BaseClient, BaseConnectionProtocol]:
    async with one_way_client_sender as conn:
        yield one_way_client_sender, conn


@pytest.fixture
async def two_way_client_connected(two_way_client_sender, two_way_server_started) -> Tuple[
        BaseClient, BaseConnectionProtocol]:
    async with two_way_client_sender as conn:
        yield two_way_client_sender, conn


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
def simple_network_connections(queue, peer_str) -> List[SimpleNetworkConnectionType]:
    return [SimpleNetworkConnection(peer_str, "TCP Server 127.0.0.1:8888", queue),
            SimpleNetworkConnection('127.0.0.1:4444', "TCP Server 127.0.0.1:8888", queue)]


@pytest.fixture
def simple_network_connection(simple_network_connections) -> SimpleNetworkConnectionType:
    return simple_network_connections[0]
