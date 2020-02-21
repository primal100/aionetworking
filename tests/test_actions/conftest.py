import asyncio
from aionetworking import FileStorage, BufferedFileStorage
from aionetworking.actions import ManagedFile
from aionetworking.actions import EchoAction
from tests.test_formats.conftest import *

from typing import List, Dict, Optional


@pytest.fixture
async def managed_file(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.open(path, mode='ab', buffering=0)
    yield f
    if not f.is_closing():
        await f.close()


@pytest.fixture
async def file_storage_action(tmp_path) -> FileStorage:
    action = FileStorage(base_path=tmp_path / 'data',
                         path='Encoded/{msg.name}/{msg.address}_{msg.uid}.{msg.name}')
    yield action


@pytest.fixture
async def buffered_file_storage_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path / 'data', close_file_after_inactivity=2,
                                 path='Encoded/{msg.address}_{msg.name}.{msg.name}', buffering=0)
    yield action
    if not action.is_closing():
        await action.close()


@pytest.fixture
async def buffered_file_storage_recording_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=Path(tmp_path / 'recordings'), close_file_after_inactivity=2,
                                 path='{msg.address}.recording', buffering=0)
    yield action
    if not action.is_closing():
        await action.close()
    await asyncio.sleep(1)


@pytest.fixture
def buffer_objects(json_encoded_multi, buffer_codec, timestamp):
    return [buffer_codec.from_decoded(decoded, received_timestamp=timestamp) for decoded in json_encoded_multi]


@pytest.fixture
def echo() -> dict:
    return {'id': 1, 'method': 'echo'}


@pytest.fixture
def echo_response() -> dict:
    return {'id': 1, 'result': 'echo'}


@pytest.fixture
def echo_notification_request() -> dict:
    return {'method': 'send_notification'}


@pytest.fixture
def echo_notification() -> dict:
    return {'result': 'notification'}


@pytest.fixture
def echo_exception_request() -> dict:
    return {'id': 1, 'method': 'echo_typo'}


@pytest.fixture
def echo_exception_response() -> dict:
    return {'id': 1, 'error': 'InvalidRequestError'}


@pytest.fixture
def echo_encoded_multi(echo, echo_notification_request) -> List[Dict]:
    return [echo, echo_notification_request]


@pytest.fixture
def echo_encoded() -> bytes:
    return b'{"id": 1, "method": "echo"}'


@pytest.fixture
def echo_request_object(echo_encoded, echo) -> JSONObject:
    return JSONObject(echo_encoded, echo)


@pytest.fixture
def echo_response_encoded() -> bytes:
    return b'{"id": 1, "result": "echo"}'


@pytest.fixture
def echo_response_object(echo_response_encoded, echo_response) -> JSONObject:
    return JSONObject(echo_response_encoded, echo_response)


@pytest.fixture
def echo_notification_client_encoded() -> bytes:
    return b'{"method": "send_notification"}'


@pytest.fixture
def echo_notification_request_object(echo_notification_client_encoded, echo_notification_request, context) -> JSONObject:
    return JSONObject(echo_notification_client_encoded, echo_notification_request, context=context)


@pytest.fixture
def echo_notification_server_encoded() -> bytes:
    return b'{"result": "notification"}'


@pytest.fixture
def echo_notification_object(echo_notification_server_encoded, echo_notification) -> JSONObject:
    return JSONObject(echo_notification_server_encoded, echo_notification)


@pytest.fixture
def echo_exception_request_encoded() -> bytes:
    return b'{"id": 1, "method": "echo_typo"}'


@pytest.fixture
def echo_exception_request_object(echo_exception_request_encoded, echo_exception_request) -> JSONObject:
    return JSONObject(echo_exception_request_encoded, echo_exception_request)


@pytest.fixture
def echo_exception_response_encoded() -> bytes:
    return b'{"id": 1, "error": "InvalidRequestError"}'


@pytest.fixture
def echo_exception_response_object(echo_exception_response_encoded, echo_exception_response) -> JSONObject:
    return JSONObject(echo_exception_response_encoded, echo_exception_response)


@pytest.fixture
def echo_request_invalid_json(echo) -> bytes:
    return b'{"id": 1, "method": echo"}'


@pytest.fixture
def echo_decode_error_response(echo_request_invalid_json) -> Dict:
    return {'error': 'JSON was invalid'}


@pytest.fixture
async def echo_action(tmp_path) -> FileStorage:
    action = EchoAction()
    yield action


class JSONObjectWithKeepAlive(JSONObject):
    @property
    def store(self) -> bool:
        return self.decoded['method'] != 'keepalive'

    @property
    def response(self) -> Optional[Dict[str, Any]]:
        if self.decoded['method'] == 'keepalive':
            return {'result': 'keepalive-response'}
        return None


@pytest.fixture
def keep_alive_request_decoded() -> Dict[str, str]:
    return {'method': 'keepalive'}


@pytest.fixture
def keep_alive_request_encoded() -> bytes:
    return b'{"method": "keepalive"}'


@pytest.fixture
def keepalive_object(keep_alive_request_encoded, keep_alive_request_decoded, context, timestamp) -> JSONObjectWithKeepAlive:
    return JSONObjectWithKeepAlive(keep_alive_request_encoded, keep_alive_request_decoded, context=context,
            received_timestamp=timestamp)
