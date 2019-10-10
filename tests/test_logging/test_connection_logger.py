import pytest
import logging


class TestConnectionLogger:
    def test_00_logger_init(self, connection_logger, context):
        assert connection_logger.logger.name == 'receiver.connection'

    def test_01_process(self, connection_logger, context):
        msg, kwargs = connection_logger.process("Hello World", {})
        assert kwargs['extra']['taskname'] == "No Running Loop"
        assert msg, kwargs == ("Hello World", {'extra': context})

    def test_02_new_connection(self, connection_logger, caplog):
        connection_logger.new_connection()
        assert caplog.record_tuples[0] == (
            "receiver.connection", logging.INFO, 'New TCP Server connection from 127.0.0.1:60000 to 127.0.0.1:8888')

    def test_03_log_received_msgs(self, connection_logger, json_object, caplog, debug_logging):
        logging.getLogger('receiver.data_received').setLevel(logging.CRITICAL)
        caplog.handler.setFormatter(logging.Formatter("{data.uid}", style='{'))
        logging.getLogger('receiver.connection').setLevel(logging.CRITICAL)
        logging.getLogger('receiver.data_received').setLevel(logging.DEBUG)
        connection_logger.on_msg_decoded(json_object)
        assert caplog.text == "1\n"

    def test_04_sending_decoded_msg(self, connection_logger, json_object, caplog, debug_logging):
        caplog.handler.setFormatter(logging.Formatter("{data.uid}", style='{'))
        connection_logger.on_sending_decoded_msg(json_object)
        assert caplog.text == "1\n"

    def test_05_on_sending_encoded_msg(self, caplog, json_rpc_login_request_encoded,
                                       connection_logger, debug_logging):
        connection_logger.on_sending_encoded_msg(json_rpc_login_request_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Sending message')
        if isinstance(json_rpc_login_request_encoded, bytes):
            json_rpc_login_request_encoded = json_rpc_login_request_encoded.decode()
        assert caplog.record_tuples[1] == ('receiver.raw_sent', logging.DEBUG, json_rpc_login_request_encoded)


class TestConnectionLoggerNoStats:
    @pytest.mark.asyncio
    async def test_00_has_no_stats(self, receiver_connection_logger):
        assert not hasattr(receiver_connection_logger, '_stats_logger')

    def test_01_on_buffer_received(self, receiver_connection_logger, caplog, json_rpc_login_request_encoded,
                                   debug_logging):
        receiver_connection_logger.on_buffer_received(json_rpc_login_request_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.INFO, 'Received buffer containing 79 bytes')
        if isinstance(json_rpc_login_request_encoded, bytes):
            json_rpc_login_request_encoded = json_rpc_login_request_encoded.decode()
        assert caplog.record_tuples[1] == ('receiver.raw_received', logging.DEBUG, json_rpc_login_request_encoded)

    def test_02_on_msg_processed(self, receiver_connection_logger, json_object, caplog):
        receiver_connection_logger.on_msg_processed(json_object)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Finished processing message 1')

    def test_03_on_msg_sent(self, receiver_connection_logger, caplog, json_rpc_logout_request_encoded):
        receiver_connection_logger.on_msg_sent(json_rpc_logout_request_encoded)
        assert caplog.record_tuples == [('receiver.connection', logging.DEBUG, 'Message sent')]

    def test_04_connection_finished_no_error(self, receiver_connection_logger, caplog):
        receiver_connection_logger.connection_finished()
        assert caplog.record_tuples == [('receiver.connection', logging.INFO,
                                         'TCP Server connection from 127.0.0.1:60000 to 127.0.0.1:8888 has been closed')]

    def test_05_connection_finished_with_error(self, receiver_connection_logger, zero_division_exception, caplog):
        receiver_connection_logger.connection_finished(zero_division_exception)
        log = caplog.record_tuples[0]
        assert log[0] == 'receiver.connection'
        assert log[1] == logging.ERROR
        assert 'ZeroDivisionError: division by zero' in log[2]
        assert caplog.record_tuples[1] == ('receiver.connection', logging.INFO,
                                        'TCP Server connection from 127.0.0.1:60000 to 127.0.0.1:8888 has been closed')


class TestConnectionLoggerStats:
    @pytest.mark.asyncio
    async def test_00_has_stats_logger(self, receiver_connection_logger_stats, stats_logger):
        assert receiver_connection_logger_stats._stats_logger == stats_logger

    def test_01_on_buffer_received(self, receiver_connection_logger_stats, json_rpc_login_request_encoded, caplog, debug_logging):
        assert receiver_connection_logger_stats._stats_logger.received == 0
        receiver_connection_logger_stats.on_buffer_received(json_rpc_login_request_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.INFO, 'Received buffer containing 79 bytes')
        if isinstance(json_rpc_login_request_encoded, bytes):
            json_rpc_login_request_encoded = json_rpc_login_request_encoded.decode()
        assert caplog.record_tuples[1] == ('receiver.raw_received', logging.DEBUG, json_rpc_login_request_encoded)
        assert receiver_connection_logger_stats._stats_logger.received == 79

    def test_02_on_msg_processed(self, receiver_connection_logger_stats, json_object, caplog):
        assert receiver_connection_logger_stats._stats_logger.processed == 0
        receiver_connection_logger_stats.on_msg_processed(json_object)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Finished processing message 1')
        assert receiver_connection_logger_stats._stats_logger.processed == 79

    def test_03_on_msg_sent(self, receiver_connection_logger_stats, caplog, json_rpc_login_request_encoded, debug_logging):
        assert receiver_connection_logger_stats._stats_logger.msgs.sent == 0
        receiver_connection_logger_stats.on_msg_sent(json_rpc_login_request_encoded)
        assert caplog.record_tuples == [('receiver.connection', logging.DEBUG, 'Message sent')]
        assert receiver_connection_logger_stats._stats_logger.msgs.sent == 1

    def test_04_connection_finished_no_error(self, receiver_connection_logger_stats, caplog):
        receiver_connection_logger_stats.connection_finished()
        assert caplog.record_tuples[0] == ('receiver.connection', logging.INFO,
                                           'TCP Server connection from 127.0.0.1:60000 to 127.0.0.1:8888 has been closed')
        assert caplog.record_tuples[1] == ('receiver.stats', logging.INFO, 'ALL')

    def test_05_connection_finished_with_error(self, receiver_connection_logger_stats, zero_division_exception, caplog):
        receiver_connection_logger_stats.connection_finished(zero_division_exception)
        log = caplog.record_tuples[0]
        assert log[0] == 'receiver.connection'
        assert log[1] == logging.ERROR
        assert 'ZeroDivisionError: division by zero' in log[2]
        assert caplog.record_tuples[1] == ('receiver.connection', logging.INFO,
                                        'TCP Server connection from 127.0.0.1:60000 to 127.0.0.1:8888 has been closed')
        assert caplog.record_tuples[2] == ('receiver.stats', logging.INFO, 'ALL')


