import pytest

from lib.actions.file_storage import ManagedFile, FileStorage, BufferedFileStorage
from tests.test_formats.conftest import *


@pytest.fixture
async def managed_file(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.open(path, mode='ab')
    yield f
    if not f.is_closing():
        await f.close()


@pytest.fixture
async def file_storage_action(tmp_path) -> FileStorage:
    action = FileStorage(base_path=tmp_path, binary=True,
                         path='Encoded/{msg.name}/{msg.sender}_{msg.uid}.{msg.name}')
    yield action


@pytest.fixture
async def buffered_file_storage_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=Path(tmp_path / 'Data'), binary=True, close_file_after_inactivity=2,
                                 path='Encoded/{msg.sender}_{msg.name}.{msg.name}')
    yield action
    if not action.is_closing():
        await action.close()


@pytest.fixture
async def buffered_file_storage_recording_action(tmp_path) -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=Path(tmp_path / 'Recordings'), binary=True, close_file_after_inactivity=2,
                                 path='{msg.sender}.recording')
    yield action
    if not action.is_closing():
        await action.close()


@pytest.fixture
def buffer_objects(json_encoded_multi, buffer_codec, timestamp):
    return [buffer_codec.from_decoded(decoded, received_timestamp=timestamp) for decoded in json_encoded_multi]
