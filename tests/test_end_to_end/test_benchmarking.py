from pathlib import Path
import asyncio
import pytest
import concurrent.futures


@pytest.mark.asyncio
async def test_00_tcp_server_benchmark(connections_manager, receiver_debug_logging_extended,
                                       one_way_server_started_benchmark, tcp_client_one_way,
                                       tmp_path, asn_buffer, asn_encoded_multi):
    num = 2
    num_clients = 5
    msgs = []
    for _ in range(0, num):
        msgs += asn_encoded_multi
    with concurrent.futures.ProcessPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        futs = []
        for i in range(0, num_clients):
            override = {'srcip': f'127.0.0.{i + 1}'}
            fut = loop.run_in_executor(executor, tcp_client_one_way.open_send_msgs, msgs, 0.001, 0, override)
            futs.append(fut)
        await asyncio.wait(futs)
    await asyncio.wait_for(one_way_server_started_benchmark.wait_num_has_connected(num_clients), timeout=2)
    await asyncio.wait_for(one_way_server_started_benchmark.wait_num_connections(0), timeout=4)
    await asyncio.wait_for(one_way_server_started_benchmark.wait_all_tasks_done(), timeout=10)
    assert len(list(Path(tmp_path / 'Encoded').glob('*.TCAP_MAP'))) == num_clients
    for i in range(0, num_clients):
        expected_file = next(Path(tmp_path / 'Encoded').glob('*.TCAP_MAP'))
        assert len(expected_file.read_bytes()) == len(asn_buffer) * num
