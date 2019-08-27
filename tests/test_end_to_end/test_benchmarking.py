import multiprocessing
import asyncio
import pytest
import concurrent.futures
from lib import settings
from pathlib import Path
from tests.mock import MockFileWriter


@pytest.mark.asyncio
async def test_00_tcp_server_benchmark(connections_manager, receiver_debug_logging_extended,
                                       tcp_server_one_way_benchmark, tcp_client_one_way,
                                       tmp_path, json_rpc_login_request_encoded):
    settings.FILE_OPENER = MockFileWriter
    num = 4000
    num_clients = 1
    msgs = [json_rpc_login_request_encoded for _ in range(0, num)]
    loop = asyncio.get_event_loop()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        coros = []
        for i in range(0, num_clients):
            override = {'srcip': f'127.0.0.{i + 1}'}
            coro = loop.run_in_executor(executor, tcp_client_one_way.open_send_msgs, msgs, 0, 1, override)
            coros.append(coro)
        await asyncio.wait(coros)
    await asyncio.wait_for(tcp_server_one_way_benchmark.wait_num_has_connected(num_clients), timeout=2)
    await asyncio.wait_for(tcp_server_one_way_benchmark.wait_num_connections(0), timeout=4)
    await asyncio.wait_for(tcp_server_one_way_benchmark.wait_all_tasks_done(), timeout=10)
    """assert len(list(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))) == num_clients
    for i in range(0, num_clients):
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert len(expected_file.read_bytes()) == len(json_rpc_login_request_encoded) * num"""
