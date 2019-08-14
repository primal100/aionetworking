from dataclasses import asdict
import logging
import pytest
import pickle

from lib.compatibility import get_current_task_name


class TestLogger:
    def test_00_init(self, receiver_logger):
        assert receiver_logger.logger.name == 'receiver'
        assert receiver_logger.extra == {}
        assert receiver_logger.datefmt == '%Y-%M-%d %H:%M:%S'

    @pytest.mark.asyncio
    async def test_01_process(self, receiver_logger):
        msg, kwargs = receiver_logger.process('Hello World', {})
        taskname = get_current_task_name()
        assert msg, kwargs == ('Hello World', {'extra': {'taskname': taskname}})

    def test_02_update_extra(self, receiver_logger):
        receiver_logger.update_extra(endpoint='TCP Server 127.0.0.1:8888')
        assert receiver_logger.extra == {'endpoint': 'TCP Server 127.0.0.1:8888'}
        msg, kwargs = receiver_logger.process('Hello World', {})
        assert msg, kwargs == (
        'Hello World', {'extra': {'taskname': 'No Running Loop', 'endpoint': 'TCP Server 127.0.0.1:8888'}})

    def test_03_manage_error(self, receiver_logger, caplog, zero_division_exception) -> None:
        receiver_logger.manage_error(zero_division_exception)
        log = caplog.record_tuples[0]
        assert log[0] == 'receiver'
        assert log[1] == logging.ERROR
        assert 'ZeroDivisionError: division by zero' in log[2]

    def test_04_manage_critical_error(self, receiver_logger, caplog, zero_division_exception) -> None:
        receiver_logger.manage_critical_error(zero_division_exception)
        log = caplog.record_tuples[0]
        assert log[0] == 'receiver'
        assert log[1] == logging.CRITICAL
        assert 'ZeroDivisionError: division by zero' in log[2]

    def test_05_log_num_connections(self, receiver_logger, caplog, debug_logging):
        receiver_logger.log_num_connections("closed", "TCP Server localhost:8888")
        assert caplog.record_tuples[0] == (
            'receiver', logging.DEBUG, 'Connection closed. There are now no active connections.')

    def test_06_get_connection_logger(self, receiver_logger, receiver_connection_logger, context):
        conn_logger = receiver_logger.get_connection_logger(is_receiver=True, extra=context)
        assert conn_logger == receiver_connection_logger

    def test_07_get_connection_logger(self, sender_logger, sender_connection_logger, client_context):
        conn_logger = sender_logger.get_connection_logger(is_receiver=False, extra=client_context)
        assert conn_logger == sender_connection_logger

    def test_08_pickle(self, receiver_logger):
        p = pickle.dumps(receiver_logger, protocol=4)
        logger = pickle.loads(p)
        assert receiver_logger == logger

    def test_09_pickle_is_closing(self, receiver_logger):
        receiver_logger._set_closing()
        p = pickle.dumps(receiver_logger, protocol=4)
        logger = pickle.loads(p)
        assert receiver_logger == logger
