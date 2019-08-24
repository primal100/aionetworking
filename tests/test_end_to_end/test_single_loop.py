import asyncio
import pytest
from pathlib import Path

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, connections_manager, server_started,
                                              client, json_rpc_login_request_encoded,
                                              tmp_path, json_buffer, json_decoded_multi, json_recording_data):
        async with client as conn:
            conn.encode_and_send_msgs(json_decoded_multi)
        await asyncio.wait_for(server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        recording_file = Path(tmp_path / 'Recordings/127.0.0.1.recording')
        assert recording_file.exists()
        expected_file = Path(tmp_path / 'Data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        assert expected_file.read_bytes() == json_buffer
        expected_file.unlink()
        new_recording_path = tmp_path / 'Recordings/127.0.0.1_new.recording'
        recording_file.rename(new_recording_path)
        async with client as conn:
            await conn.play_recording(new_recording_path)
        await asyncio.wait_for(server_started.wait_num_has_connected(2), timeout=1)
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        assert expected_file.exists()
        assert Path(expected_file).read_bytes() == json_buffer

    @pytest.mark.asyncio
    async def test_01_send_and_send_recording_debug_logging(self, connections_manager, receiver_debug_logging_extended,
                                                            server_started, client,
                                                            asn_one_encoded, tmp_path, asn_buffer, asn_encoded_multi,
                                                            json_recording_data, recording_file_name, asn_file_name):
        msgs = []
        num = 1
        for i in range(0, num):
            msgs += asn_encoded_multi
        async with client as conn:
            for msg in msgs:
                conn.send_data(msg)
                await asyncio.sleep(0.00025)
        await asyncio.wait_for(server_started.wait_num_has_connected(1), timeout=1)
        conn.close()
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Encoded').glob('*.TCAP_MAP'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(asn_buffer) * num

