from __future__ import annotations
import pytest
from pathlib import Path
from lib.formats.contrib.json import JSONObject, JSONCodec, JSONBCodec, JSONBObject
from lib.formats.recording import BufferCodec, BufferObject, recorded_packet
from lib.formats.types import MessageObjectType

from typing import AnyStr, Dict, Any, List, NamedTuple, Type


@pytest.fixture(params=[True, False])
def is_text(request) -> bool:
    return request.param


@pytest.fixture
def codec_class(is_text) -> Type[JSONCodec]:
    if is_text:
        return JSONCodec
    return JSONBCodec


@pytest.fixture
def object_class(is_text) -> Type[MessageObjectType]:
    if is_text:
        return JSONObject
    return JSONBObject


@pytest.fixture
def json_codec(codec_class, object_class, context) -> JSONBCodec:
    return codec_class(object_class, context=context)


@pytest.fixture
def json_rpc_login_request(user1, is_text) -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1}


@pytest.fixture
def json_rpc_login_request_encoded(user1, is_text) -> AnyStr:
    text = '{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'
    if is_text:
        return text
    return text.encode()


@pytest.fixture
def json_rpc_logout_request(user1) -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 2, 'method': 'logout'}


@pytest.fixture
def json_rpc_logout_request_encoded(user1, is_text) -> AnyStr:
    text = '{"jsonrpc": "2.0", "id": 2, "method": "logout"}'
    if is_text:
        return text
    return text.encode()


@pytest.fixture
def json_buffer(is_text) -> AnyStr:
    text = '{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}{"jsonrpc": "2.0", "id": 2, "method": "logout"}'
    if is_text:
        return text
    return text.encode()


@pytest.fixture
def json_encoded_multi(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[AnyStr]:
    return [
        json_rpc_login_request_encoded,
        json_rpc_logout_request_encoded
    ]


@pytest.fixture
def json_decoded_multi(json_rpc_login_request, json_rpc_logout_request) -> List[dict]:
    return [
        json_rpc_login_request,
        json_rpc_logout_request
    ]


@pytest.fixture
def decoded_result(json_encoded_multi, json_decoded_multi):
    return [(json_encoded_multi[0], json_decoded_multi[0]), (json_encoded_multi[1], json_decoded_multi[1])]


@pytest.fixture
def file_containing_multi_json(tmpdir, json_buffer, is_text) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("json"))
    if is_text:
        p.write_text(json_buffer)
    else:
        p.write_bytes(json_buffer)
    return p


@pytest.fixture
def json_object(json_rpc_login_request_encoded, json_rpc_login_request, object_class, context, timestamp) -> MessageObjectType:
    return object_class(json_rpc_login_request_encoded, json_rpc_login_request, context=context, received_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, object_class, timestamp, context) -> List[MessageObjectType]:
    return [object_class(encoded, json_decoded_multi[i], context=context,
                       received_timestamp=timestamp) for i, encoded in
            enumerate(json_encoded_multi)]


@pytest.fixture
def json_recording_data(json_rpc_login_request_encoded, json_rpc_logout_request_encoded, timestamp, is_text) -> List[NamedTuple]:
    if is_text:
        data1 = json_rpc_login_request_encoded.encode()
        data2 = json_rpc_logout_request_encoded.encode()
    else:
        data1 = json_rpc_login_request_encoded
        data2 = json_rpc_logout_request_encoded
    return [recorded_packet(sent_by_server=False, timestamp=timestamp, sender='127.0.0.1', is_bytes=not is_text, data=data1),
            recorded_packet(sent_by_server=False, timestamp=timestamp, sender='127.0.0.1', is_bytes=not is_text, data=data2)]


@pytest.fixture
def buffer_codec(context) -> BufferCodec:
    return BufferCodec(BufferObject, context=context)


@pytest.fixture
def json_encoded_multi(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[AnyStr]:
    return [
        json_rpc_login_request_encoded,
        json_rpc_logout_request_encoded
    ]

