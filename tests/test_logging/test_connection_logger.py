import asyncio
import pytest
import logging


class TestConnectionLogger:
    def test_00_logger_init(self, connection_logger, context):
        assert connection_logger.logger.name == 'receiver.connection'

    def test_01_get_extra_inet(self, connection_logger, context, tcp_server_extra):
        extra = connection_logger.get_extra(context, True)
        assert extra == tcp_server_extra

    def test_02_get_extra_unix_server(self, connection_logger, unix_socket_context, unix_server_extra):
        extra = connection_logger.get_extra(unix_socket_context, True)
        assert extra == unix_server_extra

    def test_03_get_extra_pipe(self, connection_logger, context_windows_pipe, windows_pipe_extra):
        extra = connection_logger.get_extra(context_windows_pipe, True)
        assert extra == windows_pipe_extra

    def test_04_process(self, connection_logger, tcp_server_extra):
        msg, kwargs = connection_logger.process("Hello World", {})
        tcp_server_extra['taskname'] = "No Running Loop"
        assert msg, kwargs == ("Hello World", {'extra': tcp_server_extra})

    def test_05_new_connection(self, connection_logger, caplog):
        connection_logger.new_connection()
        assert caplog.record_tuples[0] == (
            "receiver.connection", logging.INFO, 'New TCP Server connection from 127.0.0.1:60000 to 127.0.0.1:8888')

    def test_06_log_received_msgs(self, connection_logger, asn_objects, caplog, debug_logging):
        logging.getLogger('receiver.data_received').setLevel(logging.CRITICAL)
        connection_logger.log_msgs(asn_objects)
        assert caplog.record_tuples == [('receiver.connection', 10, 'Buffer contains 4 messages')]
        caplog.clear()
        caplog.handler.setFormatter(logging.Formatter("{data.uid}", style='{'))
        logging.getLogger('receiver.connection').setLevel(logging.CRITICAL)
        logging.getLogger('receiver.data_received').setLevel(logging.DEBUG)
        connection_logger.log_msgs(asn_objects)
        assert caplog.text == """00000001
840001ff
a5050001
00000000
"""

    def test_07_sending_decoded_msg(self, connection_logger, asn_object, caplog, debug_logging):
        caplog.handler.setFormatter(logging.Formatter("{data.uid}", style='{'))
        connection_logger.on_sending_decoded_msg(asn_object)
        assert caplog.text == "00000001\n"

    def test_08_on_sending_encoded_msg(self, caplog, asn_one_encoded, asn_one_hex, connection_logger, debug_logging):
        connection_logger.on_sending_encoded_msg(asn_one_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Sending message to 127.0.0.1:60000')
        assert caplog.record_tuples[1] == ('receiver.raw_sent', logging.DEBUG, asn_one_hex)


class TestConnectionLoggerNoStats:
    def test_00_has_no_stats(self, receiver_connection_logger): ...

    def test_00_on_buffer_received(self, receiver_connection_logger, caplog): ...

    def test_01_on_msg_processed(self, receiver_connection_logger, caplog): ...

    def test_02_on_msg_sent(self, receiver_connection_logger, caplog): ...

    def test_03_connection_finished(self, receiver_connection_logger, caplog): ...


class TestConnectionLoggerStats:
    def test_00_has_stats_logger(self, receiver_connection_logger_stats, caplog): ...

    def test_01_on_buffer_received(self, receiver_connection_logger_stats, caplog): ...

    def test_02_on_msg_processed(self, receiver_connection_logger_stats, caplog): ...

    def test_03_on_msg_sent(self, receiver_connection_logger_stats, caplog): ...

    def test_04_connection_finished(self, receiver_connection_logger_stats, caplog): ...

    @pytest.mark.asyncio
    async def test_05_stats_logging(self, receiver_connection_logger_stats, asn_buffer, stats_formatter, caplog):
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(asn_buffer)
        stats_logger.on_msg_processed(326)
        assert stats_logger.received == 326
        assert stats_logger.processed == 326
        await asyncio.sleep(0.15)
        assert caplog.text == "127.0.0.1 INTERVAL 1 1 0.32KB 0.32KB 0.32KB/s 0.32KB 1\n"
        assert stats_logger.received == 0
        assert stats_logger.processed == 0
