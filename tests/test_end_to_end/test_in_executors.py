import asyncio
import concurrent.futures
import pytest
from pathlib import Path
from lib.utils import supports_pipe_or_unix_connections


class TestSenderInExecutors:
    @pytest.mark.asyncio
    @pytest.mark.skipif(isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop),
                        reason="Event loops only run in main thread for Proactor")
    async def test_00_send_in_loop_in_other_thread(self, connections_manager, receiver_debug_logging_extended,
                                                   one_way_server_started, one_way_client_sender,
                                                   asn_one_encoded,
                                                   tmp_path, asn_encoded_multi, asn_decoded_multi, asn1_recording,
                                                   recording_file_name, asn_buffer, asn_file_name):
        msgs = []
        num = 1000
        for i in range(0, num):
            msgs += asn_encoded_multi
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, one_way_client_sender.open_send_msgs,
                                                           msgs, None)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Encoded').glob('*.TCAP_MAP'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(asn_buffer) * num

    @pytest.mark.asyncio
    async def test_01_send_in_other_process(self, connections_manager, receiver_debug_logging_extended,
                                            one_way_server_started, one_way_client_sender,
                                            asn_one_encoded,
                                            tmp_path, asn_encoded_multi, asn_decoded_multi, asn1_recording,
                                            recording_file_name, asn_buffer, asn_file_name):
        num = 1000
        msgs = []
        for i in range(0, num):
            msgs += asn_encoded_multi
        with concurrent.futures.ProcessPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, one_way_client_sender.open_send_msgs, msgs, 0)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Encoded').glob('*.TCAP_MAP'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(asn_buffer) * num

