import pytest
import logging
from tests.conftest import get_fixture
from tests.test_formats.conftest import *

from lib.conf.logging import Logger, ConnectionLogger, ConnectionLoggerStats, StatsTracker, StatsLogger


@pytest.fixture
async def receiver_logger() -> Logger:
    logger = Logger(logger_name='receiver', stats_interval=0.1, stats_fixed_start_time=False)
    yield logger


@pytest.fixture
async def receiver_connection_logger(receiver_logger, context, caplog) -> ConnectionLogger:
    caplog.set_level(logging.DEBUG, "receiver.connection")
    yield receiver_logger.get_connection_logger(extra=context)


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
    logger = receiver_logger.get_connection_logger(extra=context)
    yield logger
    if not logger._is_closing:
        logger.connection_finished()
    await logger.wait_closed()


@pytest.fixture
def debug_logging(caplog) -> None:
    caplog.set_level(logging.DEBUG)


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
        "{host} {msg} {msgs.received} {msgs.processed} {received.kb:.2f}KB {processed.kb:.2f}KB {average_buffer_size.kb:.2f}KB {largest_buffer.kb:.2f}KB", style="{")
