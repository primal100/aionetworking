from pathlib import Path
import asyncio
import pytest
import concurrent.futures


@pytest.mark.asyncio
async def test_00_tcp_server_benchmark(connections_manager, receiver_debug_logging_extended,
                                       tcp_server_one_way_benchmark, tcp_client_one_way,
                                       tmp_path, json_rpc_login_request_encoded):
    num = 100
    num_clients = 1
    msgs = [json_rpc_login_request_encoded for _ in range(0, num)]
    loop = asyncio.get_event_loop()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futs = []
        for i in range(0, num_clients):
            override = {'srcip': f'127.0.0.{i + 1}'}
            fut = loop.run_in_executor(executor, tcp_client_one_way.open_send_msgs, msgs, 0, 0, override)
            futs.append(fut)
        await asyncio.wait(futs)
    await asyncio.wait_for(tcp_server_one_way_benchmark.wait_num_has_connected(num_clients), timeout=2)
    await asyncio.wait_for(tcp_server_one_way_benchmark.wait_num_connections(0), timeout=4)
    await asyncio.wait_for(tcp_server_one_way_benchmark.wait_all_tasks_done(), timeout=10)
    assert len(list(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))) == num_clients
    for i in range(0, num_clients):
        expected_file = next(Path(tmp_path / 'Data/Encoded').glob('*.JSON'))
        assert len(expected_file.read_bytes()) == len(json_rpc_login_request_encoded) * num
