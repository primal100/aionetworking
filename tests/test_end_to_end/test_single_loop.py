import asyncio
import concurrent.futures
import pytest
from pathlib import Path

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, connections_manager, one_way_server_started, one_way_client_connected, asn_one_encoded,
                                              tmp_path, asn_buffer, asn_decoded_multi, asn1_recording,
                                              recording_file_name, asn_file_name):
        client, conn = one_way_client_connected
        conn.encode_and_send_msgs(asn_decoded_multi)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        conn.close()
        await asyncio.wait_for(one_way_server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file = Path(tmp_path / recording_file_name)
        assert recording_file.exists()
        expected_file = Path(tmp_path / asn_file_name)
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        expected_file.unlink()
        new_recording_path = tmp_path / (recording_file_name + "2")
        recording_file.rename(new_recording_path)
        await asyncio.sleep(5)
        await client.close()
        await asyncio.wait_for(one_way_server_started.wait_num_connections(0), timeout=1)
        async with client as conn:
            await conn.play_recording(new_recording_path)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(2), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        expected_file = Path(tmp_path / asn_file_name)
        assert expected_file.exists()
        assert Path(expected_file).read_bytes() == asn_buffer

    @pytest.mark.asyncio
    async def test_01_send_and_send_recording_debug_logging(self, connections_manager, receiver_debug_logging_extended,
                                                            one_way_server_started, one_way_client_connected,
                                                            asn_one_encoded, tmp_path, asn_buffer, asn_encoded_multi,
                                                            asn1_recording, recording_file_name, asn_file_name):
        msgs = []
        num = 1000
        for i in range(0, num):
            msgs += asn_encoded_multi
        client, conn = one_way_client_connected
        for msg in msgs:
            conn.send_data(msg)
            await asyncio.sleep(0.00025)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        conn.close()
        await asyncio.wait_for(one_way_server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Encoded').glob('*.TCAP_MAP'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(asn_buffer) * num

