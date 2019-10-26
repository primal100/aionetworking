import pytest
import logging
import os
from tests.conftest import get_fixture
from tests.test_formats.conftest import *

from lib.conf.logging import Logger, ConnectionLogger, ConnectionLoggerStats, StatsTracker, StatsLogger
from lib.conf.log_filters import PeerFilter, MessageFilter
from lib.types import Expression


@pytest.fixture
def peer_filter(peer) -> PeerFilter:
    connection_logger = logging.getLogger('receiver.connection')
    return PeerFilter([peer[0]], [connection_logger])


@pytest.fixture
def message_filter() -> MessageFilter:
    msg_received_logger = logging.getLogger('receiver.msg_received')
    msg_logger = logging.getLogger('receiver.msg')
    return MessageFilter(Expression.from_string("method == istr login"), [msg_received_logger, msg_logger])


@pytest.fixture()
def log_record(peer, sock_str, peer_str) -> logging.LogRecord:
    record = logging.LogRecord('receiver.connection', logging.INFO, os.path.abspath(__file__), 180,
                               'New %s connection from %s to %s', ('TCP Server', peer_str, sock_str),
                               None, func='new_connection', sinfo=None)
    record.alias = peer[0]
    return record


@pytest.fixture()
def log_record_not_included(peer, sock_str) -> logging.LogRecord:
    record = logging.LogRecord('receiver.connection', logging.INFO, os.path.abspath(__file__), 180,
                               'New %s connection from %s to %s', ('TCP Server', f'127.0.0.2:{peer[1]}', sock_str),
                                None, func='new_connection', sinfo=None)
    record.alias = '127.0.0.2'
    return record


@pytest.fixture()
def log_record_msg_object(json_rpc_login_request_object) -> logging.LogRecord:
    record = logging.LogRecord('receiver.msg_received', logging.DEBUG, os.path.abspath(__file__), 180,
                               'MSG RECEIVED', (), None, func='_msg_received', sinfo=None)
    record.msg_obj = json_rpc_login_request_object
    return record


@pytest.fixture()
def log_record_msg_object_not_included(json_rpc_logout_request_object) -> logging.LogRecord:
    record = logging.LogRecord('receiver.msg_received', logging.DEBUG, os.path.abspath(__file__), 180,
                             'MSG RECEIVED', (), None, func='_msg_received', sinfo=None)
    record.msg_obj = json_rpc_logout_request_object
    return record


@pytest.fixture
async def receiver_logger() -> Logger:
    logger = Logger(name='receiver', stats_interval=0.1, stats_fixed_start_time=False)
    yield logger


@pytest.fixture
async def receiver_connection_logger(receiver_logger, context, caplog) -> ConnectionLogger:
    caplog.set_level(logging.DEBUG, "receiver.connection")
    caplog.set_level(logging.DEBUG, "receiver.msg_received")
    yield receiver_logger.get_connection_logger(extra=context)
    caplog.set_level(logging.ERROR, "receiver.connection")
    caplog.set_level(logging.ERROR, "receiver.msg_received")


@pytest.fixture
def context_wrong_peer(peer, peer_str, sock_str, sock) -> Dict[str, Any]:
    return {'protocol_name': 'TCP Server', 'endpoint': f'TCP Server {sock_str}', 'host': '127.0.0.2', 'port': peer[1],
            'peer': f'127.0.0.2:{peer[1]}', 'sock': sock_str, 'alias': '127.0.0.2', 'server': sock_str,
            'client': f'127.0.0.2:{peer[1]}', 'own': sock_str}


@pytest.fixture
async def receiver_connection_logger_wrong_peer(receiver_logger, context_wrong_peer, caplog) -> ConnectionLogger:
    caplog.set_level(logging.DEBUG, "receiver.connection")
    caplog.set_level(logging.DEBUG, "receiver.msg_received")
    yield receiver_logger.get_connection_logger(extra=context_wrong_peer)
    caplog.set_level(logging.ERROR, "receiver.connection")
    caplog.set_level(logging.ERROR, "receiver.msg_received")


@pytest.fixture
def sender_logger() -> Logger:
    return Logger('sender')


@pytest.fixture
def sender_connection_logger(sender_logger, context_client) -> ConnectionLogger:
    return sender_logger.get_connection_logger(extra=context_client)


@pytest.fixture
async def receiver_connection_logger_stats(receiver_logger, context, caplog) -> ConnectionLoggerStats:
    caplog.set_level(logging.INFO, "receiver.stats")
    caplog.set_level(logging.DEBUG, "receiver.connection")
    caplog.set_level(logging.DEBUG, "receiver.msg_received")
    logger = receiver_logger.get_connection_logger(extra=context)
    yield logger
    if not logger._is_closing:
        logger.connection_finished()
    await logger.wait_closed()
    caplog.set_level(logging.ERROR, "receiver.msg_received")
    caplog.set_level(logging.ERROR, "receiver.stats")
    caplog.set_level(logging.ERROR, "receiver.connection")


@pytest.fixture
def debug_logging(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    yield
    caplog.set_level(logging.ERROR)


@pytest.fixture
def zero_division_exception() -> BaseException:
    try:
        1 / 0
    except ZeroDivisionError as e:
        return e


@pytest.fixture(params=[receiver_connection_logger, receiver_connection_logger_stats])
def _connection_logger(request):
    return get_fixture(request)


@pytest.fixture
async def connection_logger(_connection_logger):
    yield _connection_logger


@pytest.fixture
def stats_tracker() -> StatsTracker:
    return StatsTracker()


@pytest.fixture
async def stats_logger(context) -> StatsLogger:
    logger = StatsLogger("receiver.stats", extra=context, stats_interval=0.1, stats_fixed_start_time=False)
    yield logger
    if not logger._is_closing:
        logger.connection_finished()
    await logger.wait_closed()


@pytest.fixture
def stats_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{peer} {msg} {msgs.received} {msgs.processed} {received.kb:.2f}KB {processed.kb:.2f}KB {receive_rate.kb:.2f}KB/s {processing_rate.kb:.2f}KB/s {average_buffer_size.kb:.2f}KB {msgs.receive_interval}/s {msgs.processing_time}/s {msgs.buffer_receive_rate}/s {msgs.processing_rate}/s {msgs.buffer_processing_rate}/s {largest_buffer.kb:.2f}KB",
        style="{")
