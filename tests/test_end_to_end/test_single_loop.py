import asyncio
import pytest
from pathlib import Path

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestOneWayServer:
    @pytest.mark.asyncio
    async def test_00_send_and_send_recording(self, one_way_server_started, one_way_client_connected, asn_one_encoded,
                                              tmp_path, asn_buffer, asn_decoded_multi, asn1_recording,
                                              recording_file_name, asn_file_name):
        client, conn = one_way_client_connected
        conn.encode_and_send_msgs(asn_decoded_multi)
        await asyncio.wait_for(one_way_server_started.wait_all_messages_processed(), timeout=1)
        recording_file = Path(tmp_path / recording_file_name)
        assert recording_file.exists()
        expected_file = Path(tmp_path / asn_file_name)
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        expected_file.unlink()
        new_recording_path = tmp_path / (recording_file_name + "2")
        recording_file.rename(new_recording_path)
        await conn.play_recording(new_recording_path)
        await asyncio.wait_for(one_way_server_started.wait_all_messages_processed(), timeout=1)
        expected_file = Path(tmp_path / asn_file_name)
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer

