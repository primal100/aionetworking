import pytest

from lib.actions.file_storage import ManagedFile, FileStorage, BufferedFileStorage
from tests.test_formats.conftest import *


@pytest.fixture
def append_mode(is_text) -> str:
    return 'a' if is_text else 'ab'


@pytest.fixture
def read_mode(is_text) -> str:
    return 'r' if is_text else 'rb'


@pytest.fixture
async def managed_file(tmp_path, append_mode) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.open(path, timeout=None, mode=append_mode)
    yield f
    if not f.is_closing():
        await f.close()


@pytest.fixture
async def file_storage_action(tmp_path, is_text) -> FileStorage:
    action = FileStorage(base_path=tmp_path, binary=not is_text,
                         path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')
    yield action


@pytest.fixture
async def buffered_file_storage_action(tmp_path, is_text) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=not is_text, path='Encoded/{msg.sender}_{msg.name}.{msg.name}')
    yield action
    await action.close()


@pytest.fixture
async def buffered_file_storage_recording_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=tmp_path, binary=True, path='{msg.sender}.recording')
    yield action
    await action.close()


@pytest.fixture
def buffer_objects(json_encoded_multi, buffer_codec, timestamp):
    return [buffer_codec.from_decoded(decoded, received_timestamp=timestamp) for decoded in json_encoded_multi]
