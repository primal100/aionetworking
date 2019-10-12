import logging
import pytest
import asyncio


class TestStatsTracker:
    def test_00_on_buffer_received_msg_processed(self, stats_tracker, json_buffer, json_rpc_login_request_encoded,
                                                 json_rpc_logout_request_encoded):
        assert not stats_tracker.msgs.first_received
        assert not stats_tracker.msgs.last_received
        assert stats_tracker.received == 0
        stats_tracker.on_buffer_received(json_buffer)
        assert stats_tracker.msgs.first_received
        assert stats_tracker.msgs.last_received
        assert stats_tracker.msgs.received == 1
        assert stats_tracker.received == 126
        assert stats_tracker.processed == 0
        stats_tracker.on_msg_processed(json_rpc_login_request_encoded)
        assert stats_tracker.msgs.last_processed >= stats_tracker.msgs.last_received
        assert stats_tracker.msgs.processed == 1
        assert stats_tracker.processed == 79
        assert stats_tracker.processing_rate.bytes == 79.0
        assert stats_tracker.receive_rate.bytes == 126.0
        assert int(stats_tracker.interval) <= 1
        assert stats_tracker.average_buffer_size.bytes == 126.0
        assert stats_tracker.msgs.filtered == 0
        assert stats_tracker.filtered == 0
        stats_tracker.on_msg_filtered(json_rpc_logout_request_encoded)
        assert stats_tracker.msgs.filtered == 1
        assert stats_tracker.filtered == 47.0

    def test_01_on_msg_sent(self, stats_tracker, json_rpc_login_request_encoded):
        assert stats_tracker.msgs.sent == 0
        stats_tracker.on_msg_sent(json_rpc_login_request_encoded)
        assert stats_tracker.msgs.sent == 1
        assert stats_tracker.msgs.first_sent
        assert stats_tracker.sent == 79
        assert stats_tracker.average_sent == 79.0

    def test_02_end_interval(self, stats_tracker):
        assert not stats_tracker.end
        stats_tracker.end_interval()
        assert stats_tracker.end

    def test_03_iterkeys(self, stats_tracker):
        d = {}
        for key in stats_tracker:
            d[key] = stats_tracker[key]
        assert list(d) == ['start', 'end', 'msgs', 'sent', 'received', 'processed', 'filtered', 'failed',
                           'largest_buffer', 'send_rate', 'processing_rate', 'receive_rate', 'interval',
                           'average_buffer_size', 'average_sent', 'msgs_per_buffer', 'not_decoded', 'not_decoded_rate',
                           'total_done']


class TestStatsLogger:
    @pytest.mark.asyncio
    async def test_00_process(self, stats_logger):
        msg, kwargs = stats_logger.process("abc", {})
        assert msg == 'abc'
        keys = list(kwargs['extra'].keys())
        assert sorted(keys) == sorted(
            ['alias', 'average_buffer_size', 'average_sent', 'client', 'end', 'endpoint', 'failed', 'filtered', 'host',
             'interval', 'largest_buffer', 'msgs', 'msgs_per_buffer', 'not_decoded', 'not_decoded_rate', 'peer', 'port',
             'processed', 'processing_rate', 'protocol_name', 'receive_rate', 'received', 'send_rate', 'sent', 'server',
             'sock', 'start', 'taskname', 'total_done'])

    @pytest.mark.asyncio
    async def test_01_reset(self, stats_logger, json_rpc_login_request_encoded):
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        assert stats_logger.received == 79
        assert stats_logger.processed == 79
        stats_logger.reset()
        assert stats_logger.received == 0
        assert stats_logger.processed == 0

    @pytest.mark.asyncio
    async def test_02_log_info_twice(self, stats_logger, json_rpc_login_request_encoded,
                                     json_rpc_logout_request_encoded, stats_formatter, caplog):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        assert stats_logger.received == 79
        assert stats_logger.processed == 79
        stats_logger.stats('ALL')
        assert caplog.text == '127.0.0.1:60000 ALL 1 1 0.08KB 0.08KB 0.08KB/s 0.08KB/s 0.08KB 0:00:00/s 0:00:00/s 1/s 1/s 1/s 0.08KB\n'
        caplog.clear()
        assert stats_logger.received == 0
        assert stats_logger.processed == 0
        stats_logger.on_buffer_received(json_rpc_logout_request_encoded)
        stats_logger.on_msg_processed(json_rpc_logout_request_encoded)
        assert stats_logger.received == 47
        assert stats_logger.processed == 47
        stats_logger.periodic_log()
        assert caplog.text == '127.0.0.1:60000 INTERVAL 1 1 0.05KB 0.05KB 0.05KB/s 0.05KB/s 0.05KB 0:00:00/s 0:00:00/s 1/s 1/s 1/s 0.05KB\n'

    @pytest.mark.asyncio
    async def test_03_periodic_log(self, stats_logger, json_rpc_login_request_encoded, stats_formatter, caplog):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        assert stats_logger.received == 79
        assert stats_logger.processed == 79
        await asyncio.sleep(0.15)
        assert caplog.text == '127.0.0.1:60000 INTERVAL 1 1 0.08KB 0.08KB 0.08KB/s 0.08KB/s 0.08KB 0:00:00/s 0:00:00/s 1/s 1/s 1/s 0.08KB\n'
        assert stats_logger.received == 0
        assert stats_logger.processed == 0

    @pytest.mark.asyncio
    async def test_04_finish_all(self, stats_logger, json_rpc_login_request_encoded, stats_formatter, caplog):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        stats_logger.connection_finished()
        assert caplog.text == '127.0.0.1:60000 ALL 1 1 0.08KB 0.08KB 0.08KB/s 0.08KB/s 0.08KB 0:00:00/s 0:00:00/s 1/s 1/s 1/s 0.08KB\n'

    @pytest.mark.asyncio
    async def test_05_interval_end(self, stats_logger, json_rpc_login_request_encoded, stats_formatter, caplog):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        await asyncio.sleep(0.15)
        assert caplog.text == '127.0.0.1:60000 INTERVAL 1 0 0.08KB 0.00KB 0.08KB/s 0.00KB/s 0.08KB 0:00:00/s 0:00:00/s 1/s 0/s 1/s 0.08KB\n'
        caplog.clear()
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        stats_logger.connection_finished()
        assert caplog.text == '127.0.0.1:60000 END 0 1 0.00KB 0.08KB 0.00KB/s 0.08KB/s 0.00KB 0:00:00/s 0:00:00/s 0/s 1/s 0/s 0.00KB\n'
