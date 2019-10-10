import json
from lib.actions.file_storage import ManagedFile, FileStorage, BufferedFileStorage
from lib.actions.echo import EchoAction
from lib.formats.contrib.json import JSONObject
from tests.test_formats.conftest import *

from typing import List, Dict


@pytest.fixture
async def managed_file(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.open(path, mode='ab', buffering=0)
    yield f
    if not f.is_closing():
        await f.close()


@pytest.fixture
async def file_storage_action(tmp_path) -> FileStorage:
    action = FileStorage(base_path=tmp_path / 'Data', binary=True,
                         path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')
    yield action


@pytest.fixture
async def buffered_file_storage_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=Path(tmp_path / 'Data'), binary=True, close_file_after_inactivity=2,
                                 path='Encoded/{msg.sender}_{msg.name}.{msg.name}', buffering=0)
    yield action
    if not action.is_closing():
        await action.close()


@pytest.fixture
async def buffered_file_storage_recording_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=Path(tmp_path / 'Recordings'), binary=True, close_file_after_inactivity=2,
                                 path='{msg.sender}.recording', buffering=0)
    yield action
    if not action.is_closing():
        await action.close()


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
def echo_request_object(echo) -> JSONObject:
    return JSONObject(json.dumps(echo), echo)


@pytest.fixture
def echo_response_object(echo_response) -> JSONObject:
    return JSONObject(json.dumps(echo_response), echo_response)


@pytest.fixture
def echo_notification_request_object(echo_notification_request) -> JSONObject:
    return JSONObject(json.dumps(echo_notification_request), echo_notification_request)


@pytest.fixture
def echo_notification_object(echo_notification) -> JSONObject:
    return JSONObject(json.dumps(echo_notification), echo_notification)


@pytest.fixture
def echo_exception_request_object(echo_exception_request) -> JSONObject:
    return JSONObject(json.dumps(echo_exception_request), echo_exception_request)


@pytest.fixture
def echo_exception_response_object(echo_exception_response) -> JSONObject:
    return JSONObject(json.dumps(echo_exception_response), echo_exception_response)


@pytest.fixture
def echo_request_invalid_json(echo) -> bytes:
    return b'{"id": 1, "method": echo"}'


@pytest.fixture
def echo_decode_error_response(echo_request_invalid_json)  -> Dict:
    return {'error': 'JSON was invalid', 'request': echo_request_invalid_json}


@pytest.fixture
async def echo_action(tmp_path) -> FileStorage:
    action = EchoAction()
    yield action
