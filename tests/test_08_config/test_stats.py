import logging
import pytest   # noinspection PyPackageRequirements
import asyncio
try:
    import psutil   # noinspection PyPackageRequirements
except ImportError:
    psutil = None


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
        assert stats_tracker.processing_rate.bytes >= 79.0
        assert stats_tracker.receive_rate.bytes >= 126.0
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
        expected_keys = ['start', 'end', 'msgs', 'sent', 'received', 'processed', 'filtered', 'failed',
                         'largest_buffer', 'send_rate', 'processing_rate', 'receive_rate', 'interval',
                         'average_buffer_size', 'average_sent', 'msgs_per_buffer', 'not_decoded', 'not_decoded_rate',
                         'total_done']
        assert sorted(list(d)) == sorted(expected_keys)


class TestStatsLogger:
    @pytest.mark.asyncio
    async def test_00_process(self, stats_logger):
        msg, kwargs = stats_logger.process("abc", {})
        assert msg == 'abc'
        keys = list(kwargs['extra'].keys())
        expected_keys = ['address', 'alias', 'average_buffer_size', 'average_sent', 'client', 'end', 'failed',
                         'filtered', 'host', 'interval', 'largest_buffer', 'msgs', 'msgs_per_buffer',
                         'not_decoded', 'not_decoded_rate', 'own', 'peer', 'port', 'processed', 'processing_rate',
                         'protocol_name', 'receive_rate', 'received', 'send_rate', 'sent', 'server',
                         'start', 'taskname', 'total_done']
        if psutil:
            expected_keys.append('system')
        assert sorted(keys) == sorted(expected_keys)

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
    async def test_02_log_info_twice(self, stats_logger, json_rpc_login_request_encoded, client_sock_str,
                                     json_rpc_logout_request_encoded, stats_formatter, caplog):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        assert stats_logger.received == 79
        assert stats_logger.processed == 79
        stats_logger.stats('ALL')
        assert caplog.text.startswith(f'{client_sock_str} ALL 1 1 0.08KB 0.08KB')
        caplog.clear()
        assert stats_logger.received == 0
        assert stats_logger.processed == 0
        stats_logger.on_buffer_received(json_rpc_logout_request_encoded)
        stats_logger.on_msg_processed(json_rpc_logout_request_encoded)
        assert stats_logger.received == 47
        assert stats_logger.processed == 47
        stats_logger.periodic_log()
        assert caplog.text.startswith(f'{client_sock_str} INTERVAL 1 1 0.05KB 0.05KB')

    @pytest.mark.asyncio
    async def test_03_periodic_log(self, stats_logger, json_rpc_login_request_encoded, stats_formatter, caplog,
                                   client_sock_str):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        assert stats_logger.received == 79
        assert stats_logger.processed == 79
        await asyncio.sleep(0.15)
        assert caplog.text.startswith(f'{client_sock_str} INTERVAL 1 1 0.08KB 0.08KB')
        assert stats_logger.received == 0
        assert stats_logger.processed == 0

    @pytest.mark.asyncio
    async def test_04_finish_all(self, stats_logger, json_rpc_login_request_encoded, stats_formatter, caplog,
                                 client_sock_str):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        stats_logger.connection_finished()
        assert caplog.text.startswith(f'{client_sock_str} ALL 1 1 0.08KB 0.08KB')

    @pytest.mark.asyncio
    async def test_05_interval_end(self, stats_logger, json_rpc_login_request_encoded, stats_formatter, caplog,
                                   client_sock_str):
        caplog.clear()
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(json_rpc_login_request_encoded)
        await asyncio.sleep(0.15)
        assert caplog.text.startswith(f'{client_sock_str} INTERVAL 1 0 0.08KB 0.00KB')
        caplog.clear()
        stats_logger.on_msg_processed(json_rpc_login_request_encoded)
        stats_logger.connection_finished()
        assert caplog.text.startswith(f'{client_sock_str} END 0 1 0.00KB 0.08KB')
