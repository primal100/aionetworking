import logging
import pytest
import pickle

from aionetworking.compatibility import get_current_task_name, py38, set_current_task_name


class TestLogger:
    def test_00_init(self, receiver_logger):
        assert receiver_logger.logger.name == 'receiver'
        assert receiver_logger.extra == {}
        assert receiver_logger.datefmt == '%Y-%m-%d %H:%M:%S.%f'

    @pytest.mark.asyncio
    async def test_01_process(self, receiver_logger):
        msg, kwargs = receiver_logger.process('Hello World', {})
        taskname = get_current_task_name()
        assert msg, kwargs == ('Hello World', {'extra': {'taskname': taskname}})

    @pytest.mark.asyncio
    @pytest.mark.skipif(not py38, reason="Task names only valid from python 3.8")
    async def test_02_process_taskname(self, receiver_logger):
        set_current_task_name("TestTask", include_hierarchy=False)
        msg, kwargs = receiver_logger.process("Hello World", {})
        assert msg, kwargs == ('Hello World', {'extra': {'taskname': "TestTask"}})

    def test_03_update_extra(self, receiver_logger, server_sock_str):
        receiver_logger.update_extra(endpoint=f'TCP Server {server_sock_str}')
        assert receiver_logger.extra == {'endpoint': f'TCP Server {server_sock_str}'}
        msg, kwargs = receiver_logger.process('Hello World', {})
        assert msg, kwargs == (
        'Hello World', {'extra': {'taskname': 'No Running Loop', 'endpoint': f'TCP Server {server_sock_str}'}})

    def test_04_manage_error(self, receiver_logger, caplog, zero_division_exception) -> None:
        receiver_logger.manage_error(zero_division_exception)
        log = caplog.record_tuples[0]
        assert log == ('receiver', logging.ERROR, 'division by zero')

    def test_05_manage_critical_error(self, receiver_logger, caplog, zero_division_exception) -> None:
        receiver_logger.manage_critical_error(zero_division_exception)
        log = caplog.record_tuples[0]
        assert log == ('receiver', logging.CRITICAL, 'division by zero')

    def test_06_log_num_connections(self, receiver_logger, caplog, debug_logging):
        receiver_logger.log_num_connections("closed", 4)
        assert caplog.record_tuples[0] == (
            'receiver', logging.DEBUG, 'Connection closed. There are now 4 active connections.')

    def test_07_get_receiver_connection_logger(self, receiver_logger, receiver_connection_logger, tcp_server_context_fixed_port):
        conn_logger = receiver_logger.get_connection_logger(extra=tcp_server_context_fixed_port)
        assert conn_logger == receiver_connection_logger

    def test_08_get_sender_connection_logger(self, sender_logger, sender_connection_logger, tcp_client_context_fixed_port):
        conn_logger = sender_logger.get_connection_logger(extra=tcp_client_context_fixed_port)
        assert conn_logger == sender_connection_logger

    def test_09_pickle(self, receiver_logger):
        p = pickle.dumps(receiver_logger, protocol=4)
        logger = pickle.loads(p)
        assert receiver_logger == logger

    def test_10_pickle_is_closing(self, receiver_logger):
        receiver_logger._set_closing()
        p = pickle.dumps(receiver_logger, protocol=4)
        logger = pickle.loads(p)
        assert receiver_logger == logger
