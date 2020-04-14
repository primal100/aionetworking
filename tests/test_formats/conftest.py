import pytest
import os
from pathlib import Path
from dataclasses import dataclass
from aionetworking import JSONObject, JSONCodec
from aionetworking.compatibility import default_server_port, default_client_port
from aionetworking.formats import BufferCodec, BufferObject, recorded_packet
from aionetworking.types.formats import MessageObjectType

from typing import Tuple, Union, List, Dict, Any, NamedTuple, Type, Optional


@pytest.fixture
def server_port() -> int:
    return default_server_port()


@pytest.fixture
def client_port() -> int:
    return default_client_port()


@pytest.fixture
def server_sock(server_port) -> Tuple[str, int]:
    return '127.0.0.1', server_port


@pytest.fixture
def client_sock(client_port) -> Tuple[str, int]:
    return '127.0.0.1', client_port


@pytest.fixture
def peer(endpoint, connection_type, server_sock, client_sock, pipe_path) -> Optional[Union[str, Tuple[str, int]]]:
    if connection_type != 'pipe':
        return client_sock if endpoint == 'server' else server_sock
    elif os.name == 'nt':
        return None
    return str(pipe_path) if endpoint == 'client' else ''


@pytest.fixture
def server_sock_str(server_sock) -> str:
    return f'{server_sock[0]}:{server_sock[1]}'


@pytest.fixture
def server_hostname(server_sock) -> str:
    return 'localhost'


@pytest.fixture
def client_hostname(client_sock) -> str:
    return 'localhost'


@pytest.fixture
def server_hostname_ip6(server_sock) -> str:
    return 'ip6-localhost'


@pytest.fixture
def client_hostname_ip6(client_sock) -> str:
    return 'ip6-localhost'


@pytest.fixture
def client_sock_str(client_sock) -> str:
    return f'{client_sock[0]}:{client_sock[1]}'


@pytest.fixture
def server_sock_ipv6(server_port) -> Tuple[str, int, int, int]:
    return '::1', server_port, 0, 0


@pytest.fixture
def client_sock_ipv6() -> Tuple[str, int, int, int]:
    return '::1', 60000, 0, 0


@pytest.fixture
def client_sock_ipv6str(client_sock_ipv6) -> str:
    return f'{client_sock_ipv6[0]}:{client_sock_ipv6[1]}'


@pytest.fixture
def json_codec(context) -> JSONCodec:
    return JSONCodec(JSONObject, context=context)


@pytest.fixture
def json_server_codec(server_context) -> JSONCodec:
    return JSONCodec(JSONObject, context=server_context)


@pytest.fixture
def user1() -> List[str]:
    return ['user1', 'password']


@pytest.fixture
def json_rpc_login_request(user1) -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1}


@pytest.fixture
async def json_rpc_logout_request_object(json_rpc_logout_request, json_codec, timestamp) -> JSONObject:
    yield await json_codec.encode_obj(json_rpc_logout_request, system_timestamp=timestamp)


@pytest.fixture
async def json_rpc_login_request_object(json_rpc_login_request, json_codec, timestamp) -> JSONObject:
    yield await json_codec.encode_obj(json_rpc_login_request, system_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_request_encoded() -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'


@pytest.fixture
def json_rpc_logout_request() -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 2, 'method': 'logout'}


@pytest.fixture
def json_rpc_logout_request_encoded(user1) -> bytes:
    return b'{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def json_buffer() -> bytes:
    # noinspection PyPep8
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
    return JSONObject(json_rpc_login_request_encoded, json_rpc_login_request, context=context,
                      system_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, timestamp, context) -> List[MessageObjectType]:
    return [JSONObject(encoded, json_decoded_multi[i], context=context,
            system_timestamp=timestamp) for i, encoded in
            enumerate(json_encoded_multi)]


@pytest.fixture
def json_server_objects(json_encoded_multi, json_decoded_multi, timestamp, server_context) -> List[MessageObjectType]:
    return [JSONObject(encoded, json_decoded_multi[i], context=server_context,
            system_timestamp=timestamp) for i, encoded in
            enumerate(json_encoded_multi)]


@pytest.fixture
def two_way_recording_data(json_rpc_login_request_encoded, json_rpc_logout_request_encoded, client_address,
                           timestamp) -> List[
                        NamedTuple]:
    return [recorded_packet(sent_by_server=False, timestamp=timestamp, sender=client_address,
                            data=b'{"id": 1, "method": "echo"}')]


@pytest.fixture
def client_address(client_sock, pipe_path, connection_type):
    if connection_type == 'pipe':
        return pipe_path.name
    return client_sock[0]


@pytest.fixture
def one_way_recording_data(json_rpc_login_request_encoded, json_rpc_logout_request_encoded, client_address,
                           timestamp) -> List[
                           NamedTuple]:
    return [recorded_packet(sent_by_server=False, timestamp=timestamp, sender=client_address,
                            data=json_rpc_login_request_encoded),
            recorded_packet(sent_by_server=False, timestamp=timestamp, sender=client_address,
                            data=json_rpc_logout_request_encoded)]


@pytest.fixture
def recording_data(one_way_recording_data, two_way_recording_data, duplex_type) -> List[recorded_packet]:
    if duplex_type == 'twoway':
        return two_way_recording_data
    return one_way_recording_data


@pytest.fixture
def buffer_codec(server_context_fixed_port) -> BufferCodec:
    return BufferCodec(BufferObject, context=server_context_fixed_port)


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
