from pathlib import Path
from aionetworking.actions import BufferedFileStorage, FileStorage, EchoAction
from typing import Dict, Callable


def get_buffered_file_storage(data_dir: Path) -> BufferedFileStorage:
    return BufferedFileStorage(base_path=data_dir, close_file_after_inactivity=2,
                               path='{msg.address}.{msg.name}', buffering=0)


def get_file_storage(data_dir: Path) -> FileStorage:
    return FileStorage(base_path=data_dir, path='{msg.address}_{msg.uid}.{msg.name}')


def get_recording_buffered_file_storage(recordings_dir: Path) -> BufferedFileStorage:
    return BufferedFileStorage(base_path=recordings_dir, close_file_after_inactivity=2,
                                 path='{msg.address}.recording', buffering=0)


file_storage_actions: Dict[str, Callable] = {
    'BufferedFileStorageAction': get_buffered_file_storage,
    'FileStorageAction': get_file_storage,
}


def get_echo_action(data_dir: Path) -> EchoAction:
    return EchoAction()


duplex_actions: Dict[str, Callable] = {
    'oneway': get_buffered_file_storage,
    'twoway': get_echo_action,
}
