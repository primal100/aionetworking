from __future__ import annotations
import pytest
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from aionetworking.formats.contrib.json import JSONObject, JSONCodec
from aionetworking.formats.recording import BufferCodec, BufferObject, recorded_packet
from aionetworking.types.formats import MessageObjectType

from typing import Dict, Any, List, NamedTuple, Tuple, Type


@pytest.fixture
def server_port() -> int:
    loop = asyncio.get_event_loop()
    if os.name == 'nt':
        if isinstance(loop, asyncio.ProactorEventLoop):
            return 8886
        if isinstance(loop, asyncio.SelectorEventLoop):
            return 8887
    if isinstance(loop, asyncio.SelectorEventLoop):
        return 8888
    else:
        return 8889


@pytest.fixture
def client_port() -> int:
    loop = asyncio.get_event_loop()
    if os.name == 'nt':
        if isinstance(loop, asyncio.ProactorEventLoop):
            return 60000
        if isinstance(loop, asyncio.SelectorEventLoop):
            return 60001
    if isinstance(loop, asyncio.SelectorEventLoop):
        return 60002
    else:
        return 60003


@pytest.fixture
def sock(server_port) -> Tuple[str, int]:
    return '127.0.0.1', server_port


@pytest.fixture
def sock_str(sock) -> str:
    return f'{sock[0]}:{sock[1]}'


@pytest.fixture
def sock_ipv6(server_port) -> Tuple[str, int, int, int]:
    return '::1', server_port, 0, 0


@pytest.fixture
def peer(client_port) -> Tuple[str, int]:
    return '127.0.0.1', client_port


@pytest.fixture
def peer_str(peer) -> str:
    return f'{peer[0]}:{peer[1]}'


@pytest.fixture
def peer_ipv6() -> Tuple[str, int, int, int]:
    return '::1', 60000, 0, 0


@pytest.fixture
def peer_ipv6str(peer_ipv6) -> str:
    return f'{peer_ipv6[0]}:{peer_ipv6[1]}'


@pytest.fixture
def context(peer, peer_str, sock, sock_str) -> Dict[str, Any]:
    return {'protocol_name': 'TCP Server', 'endpoint': f'TCP Server {sock_str}', 'host': peer[0], 'port': peer[1],
            'peer': peer_str, 'sock': sock_str, 'alias': peer[0], 'server': sock_str,
            'client': peer_str, 'own': sock_str}


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


@dataclass
class JSONCodecWithKwargs(JSONCodec):
    test_param: str = None


class JSONObjectWithCodecKwargs(JSONObject):
    codec_cls = JSONCodecWithKwargs


@pytest.fixture
def json_codec_with_kwargs() -> JSONCodecWithKwargs:
    return JSONCodecWithKwargs(JSONObjectWithCodecKwargs, test_param='abc')


@pytest.fixture
def json_object_with_codec_kwargs() -> Type[JSONObjectWithCodecKwargs]:
    return JSONObjectWithCodecKwargs
