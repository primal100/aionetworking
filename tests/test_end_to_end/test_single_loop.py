import asyncio
import pytest
from pathlib import Path

from lib.conf.logging import connection_logger_cv
from lib.formats.recording import get_recording_from_file
from lib.utils import alist

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, connections_manager, server_started,
                                              client, json_rpc_login_request_encoded, receiver_debug_logging_extended,
                                              tmp_path, json_buffer, json_decoded_multi, json_recording_data):
        async with client as conn:
            conn.encode_and_send_msgs(json_decoded_multi)
        await asyncio.wait_for(server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('Recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert expected_file.read_bytes() == json_buffer
        expected_file.unlink()
        new_recording_path = tmp_path / 'Recordings/new.recording'
        recording_file_path.rename(new_recording_path)
        async with client as conn:
            await conn.play_recording(new_recording_path)
        await asyncio.wait_for(server_started.wait_num_has_connected(2), timeout=1)
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert Path(expected_file).read_bytes() == json_buffer
