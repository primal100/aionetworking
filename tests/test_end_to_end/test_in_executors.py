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
                                                   server_started, client, json_rpc_login_request_encoded, tmp_path,
                                                   ):

        msgs = []
        num = 1
        for i in range(0, num):
            msgs += json_rpc_login_request_encoded
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, client.open_send_msgs,
                                                           msgs, None)
        await asyncio.wait_for(server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('Recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(json_rpc_login_request_encoded) * num

    @pytest.mark.asyncio
    async def test_01_send_in_other_process(self, connections_manager, server_started, client,
                                            json_rpc_login_request_encoded, tmp_path):
        num = 500
        msgs = [json_rpc_login_request_encoded for _ in range(0, num)]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, client.open_send_msgs, msgs, 0.00025, 2)
        await asyncio.wait_for(server_started.wait_num_has_connected(1), timeout=1)
        await asyncio.wait_for(server_started.wait_num_connections(0), timeout=1)
        await asyncio.wait_for(server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('Recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(json_rpc_login_request_encoded) * num

