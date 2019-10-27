import asyncio
import concurrent.futures
import pytest
from pathlib import Path
import os

###Required for skipif in fixture params###
from aionetworking.compatibility import datagram_supported, supports_pipe_or_unix_connections


class TestOneWaySenderInExecutors:
    @pytest.mark.asyncio
    @pytest.mark.skipif(os.name =='nt' and isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop),
                        reason="Event loops only run in main thread for Proactor")
    async def test_00_send_in_loop_in_other_thread(self, one_way_server_started, one_way_client,
                                                   json_rpc_login_request_encoded, tmp_path):

        num = 1
        msgs = [json_rpc_login_request_encoded for _ in range(0, num)]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, one_way_client.open_send_msgs,
                                                           msgs, None)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        one_way_server_started.close_all_connections()
        await one_way_server_started.wait_num_connections(0)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(json_rpc_login_request_encoded) * num

    @pytest.mark.asyncio
    async def test_01_send_in_other_process(self, one_way_server_started, one_way_client,
                                            json_rpc_login_request_encoded, tmp_path):
        num = 10
        msgs = [json_rpc_login_request_encoded for _ in range(0, num)]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, one_way_client.open_send_msgs, msgs, 0.00025, 2)
        await asyncio.wait_for(one_way_server_started.wait_num_has_connected(1), timeout=1)
        one_way_server_started.close_all_connections()
        await one_way_server_started.wait_num_connections(0)
        await asyncio.wait_for(one_way_server_started.wait_all_tasks_done(), timeout=1)
        recording_file_path = next(tmp_path.glob('recordings/*.recording'))
        assert recording_file_path.exists()
        expected_file = next(Path(tmp_path / 'data/Encoded').glob('*.JSON'))
        assert expected_file.exists()
        assert len(expected_file.read_bytes()) == len(json_rpc_login_request_encoded) * num


class TestTwoWaySenderInExecutors:
    @pytest.mark.asyncio
    @pytest.mark.skipif(os.name=='nt' and isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop),
                        reason="Event loops only run in main thread for Proactor")
    async def test_00_send_in_loop_in_other_thread(self, two_way_server_started, two_way_client, echo_encoded, tmp_path):

        num = 1
        msgs = [echo_encoded for _ in range(0, num)]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, two_way_client.open_send_msgs,
                                                           msgs, None, 0, None, True)
        recording_file_path = next(tmp_path.glob('recordings/*.recording'))
        assert recording_file_path.exists()

    @pytest.mark.asyncio
    async def test_01_send_in_other_process(self, two_way_server_started, two_way_client, echo_encoded, tmp_path):
        num = 10
        msgs = [echo_encoded for _ in range(0, num)]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, two_way_client.open_send_msgs, msgs, 0.00025, 2,
                                                           None, True)
        recording_file_path = next(tmp_path.glob('recordings/*.recording'))
        assert recording_file_path.exists()
