from __future__ import annotations
import pytest
from pathlib import Path
from lib.formats.contrib.json import JSONObject, JSONCodec
from lib.formats.recording import BufferCodec, BufferObject, recorded_packet
from lib.formats.types import MessageObjectType

from typing import Dict, Any, List, NamedTuple, Tuple


@pytest.fixture
def json_codec(context) -> JSONCodec:
    return JSONCodec(JSONObject, context=context)


@pytest.fixture
def json_rpc_login_request(user1) -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1}


@pytest.fixture
def json_rpc_login_request_encoded(user1) -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'


@pytest.fixture
def json_rpc_logout_request(user1) -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 2, 'method': 'logout'}


@pytest.fixture
def json_rpc_logout_request_encoded(user1) -> bytes:
    return b'{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def json_buffer() -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def json_encoded_multi(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[bytes]:
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
def decoded_result(json_encoded_multi, json_decoded_multi) -> List[Tuple[bytes, Dict[str, Any]]]:
    return [(json_encoded_multi[0], json_decoded_multi[0]), (json_encoded_multi[1], json_decoded_multi[1])]


@pytest.fixture
def file_containing_multi_json(tmpdir, json_buffer) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("json"))
    p.write_bytes(json_buffer)
    return p


@pytest.fixture
def json_object(json_rpc_login_request_encoded, json_rpc_login_request, context, timestamp) -> MessageObjectType:
    return JSONObject(json_rpc_login_request_encoded, json_rpc_login_request, context=context, received_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, timestamp, context) -> List[MessageObjectType]:
    return [JSONObject(encoded, json_decoded_multi[i], context=context,
            received_timestamp=timestamp) for i, encoded in
            enumerate(json_encoded_multi)]


@pytest.fixture
def json_recording_data(json_rpc_login_request_encoded, json_rpc_logout_request_encoded, timestamp) -> List[
                        NamedTuple]:
    return [recorded_packet(sent_by_server=False, timestamp=timestamp, sender='127.0.0.1',
                            data=json_rpc_login_request_encoded),
            recorded_packet(sent_by_server=False, timestamp=timestamp, sender='127.0.0.1',
                            data=json_rpc_logout_request_encoded)]


@pytest.fixture
def buffer_codec(context) -> BufferCodec:
    return BufferCodec(BufferObject, context=context)


@pytest.fixture
def json_encoded_multi(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[bytes]:
    return [
        json_rpc_login_request_encoded,
        json_rpc_logout_request_encoded
    ]

