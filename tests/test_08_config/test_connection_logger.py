# noinspection PyPackageRequirements
import pytest
import logging
from aionetworking.compatibility import py37


class TestConnectionLogger:
    def test_00_logger_init(self, connection_logger):
        assert connection_logger.logger.name == 'receiver.connection'

    @pytest.mark.parametrize('expected_taskname', [
        pytest.param('No Running Loop', marks=pytest.mark.skipif(not py37, reason='Only python < 3.7')),
        pytest.param('No Task', marks=pytest.mark.skipif(py37, reason='Only python=>3.7'))
    ])
    def test_01_process(self, connection_logger, context, expected_taskname):
        msg, kwargs = connection_logger.process("Hello World", {})
        assert kwargs['extra']['taskname'] == expected_taskname
        assert msg, kwargs == ("Hello World", {'extra': context})

    def test_02_new_connection(self, connection_logger, caplog, client_sock_str, server_sock_str):
        connection_logger.new_connection()
        assert caplog.record_tuples[0] == (
            "receiver.connection", logging.INFO,
            f'New TCP Server connection from {client_sock_str} to {server_sock_str}')

    def test_03_log_received_msgs(self, connection_logger, json_object, caplog, debug_logging):
        logging.getLogger('receiver.msg_received').setLevel(logging.CRITICAL)
        caplog.handler.setFormatter(logging.Formatter("{msg_obj.uid}", style='{'))
        logging.getLogger('receiver.connection').setLevel(logging.CRITICAL)
        logging.getLogger('receiver.msg_received').setLevel(logging.DEBUG)
        connection_logger.on_msg_decoded(json_object)
        assert caplog.text == "1\n"

    def test_04_sending_decoded_msg(self, connection_logger, json_object, caplog, debug_logging):
        caplog.handler.setFormatter(logging.Formatter("{msg_obj.uid}", style='{'))
        connection_logger.on_sending_decoded_msg(json_object)
        assert caplog.text == "1\n"

    def test_05_on_sending_encoded_msg(self, caplog, json_rpc_login_request_encoded,
                                       connection_logger, debug_logging):
        connection_logger.on_sending_encoded_msg(json_rpc_login_request_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Sending message')
        if isinstance(json_rpc_login_request_encoded, bytes):
            json_rpc_login_request_encoded = json_rpc_login_request_encoded.decode()
        assert caplog.record_tuples[1] == ('receiver.raw_sent', logging.DEBUG, json_rpc_login_request_encoded)

    def test_06_msg_logger(self, connection_logger, json_rpc_login_request_object, debug_logging, caplog):
        msg_logger = connection_logger.new_msg_logger(json_rpc_login_request_object)
        assert msg_logger.extra['msg_obj'] == json_rpc_login_request_object
        msg_logger.debug('Hello World')
        assert caplog.record_tuples[0] == ('receiver.msg', logging.DEBUG, 'Hello World')


class TestConnectionLoggerNoStats:
    @pytest.mark.asyncio
    async def test_00_has_no_stats(self, receiver_connection_logger):
        assert not hasattr(receiver_connection_logger, '_stats_logger')

    def test_01_on_buffer_received(self, receiver_connection_logger, caplog, json_rpc_login_request_encoded,
                                   debug_logging):
        receiver_connection_logger.on_buffer_received(json_rpc_login_request_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.INFO, 'Received buffer containing 79 bytes')

    @pytest.mark.asyncio
    async def test_02_on_buffer_decoded(self, receiver_connection_logger, caplog, json_rpc_login_request_encoded,
                                  debug_logging):
        receiver_connection_logger.on_buffer_decoded(json_rpc_login_request_encoded, 1)
        json_rpc_login_request_encoded = json_rpc_login_request_encoded.decode()
        assert caplog.record_tuples[0] == ('receiver.raw_received', logging.DEBUG, json_rpc_login_request_encoded)
        assert caplog.record_tuples[1] == ('receiver.connection', logging.INFO, "Decoded 1 message in buffer")

    @pytest.mark.asyncio
    async def test_03_on_msg_processed(self, receiver_connection_logger, json_object, caplog):
        receiver_connection_logger.on_msg_processed(json_object)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Finished processing message 1')

    @pytest.mark.asyncio
    async def test_04_on_msg_sent(self, receiver_connection_logger, caplog, json_rpc_logout_request_encoded):
        receiver_connection_logger.on_msg_sent(json_rpc_logout_request_encoded)
        assert caplog.record_tuples == [('receiver.connection', logging.DEBUG, 'Message sent')]

    @pytest.mark.asyncio
    async def test_05_connection_finished_no_error(self, receiver_connection_logger, caplog, client_sock_str,
                                             server_sock_str):
        receiver_connection_logger.connection_finished()
        # noinspection PyPep8
        assert caplog.record_tuples == [('receiver.connection', logging.INFO,
                                         f'TCP Server connection from {client_sock_str} to {server_sock_str} has been closed')]

    @pytest.mark.asyncio
    async def test_06_connection_finished_with_error(self, receiver_connection_logger, zero_division_exception, caplog,
                                               client_sock_str, server_sock_str):
        receiver_connection_logger.connection_finished(zero_division_exception)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.ERROR, 'division by zero')
        # noinspection PyPep8
        assert caplog.record_tuples[1] == ('receiver.connection', logging.INFO,
                                           f'TCP Server connection from {client_sock_str} to {server_sock_str} has been closed')


class TestConnectionLoggerStats:
    @pytest.mark.asyncio
    async def test_00_has_stats_logger(self, receiver_connection_logger_stats, stats_logger):
        assert receiver_connection_logger_stats._stats_logger == stats_logger

    @pytest.mark.asyncio
    async def test_01_on_buffer_received(self, receiver_connection_logger_stats, json_rpc_login_request_encoded, caplog,
                                   debug_logging):
        assert receiver_connection_logger_stats._stats_logger.received == 0
        receiver_connection_logger_stats.on_buffer_received(json_rpc_login_request_encoded)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.INFO, 'Received buffer containing 79 bytes')
        assert receiver_connection_logger_stats._stats_logger.received == 79

    @pytest.mark.asyncio
    async def test_02_on_buffer_decoded(self, receiver_connection_logger_stats, json_rpc_login_request_encoded,
                                        debug_logging, caplog):
        assert caplog.record_tuples == []
        receiver_connection_logger_stats.on_buffer_decoded(json_rpc_login_request_encoded, 1)
        json_rpc_login_request_encoded = json_rpc_login_request_encoded.decode()
        assert caplog.record_tuples[0] == ('receiver.raw_received', logging.DEBUG, json_rpc_login_request_encoded)
        assert caplog.record_tuples[1] == ('receiver.connection', logging.INFO, "Decoded 1 message in buffer")

    @pytest.mark.asyncio
    async def test_03_on_msg_processed(self, receiver_connection_logger_stats, json_object, caplog):
        assert receiver_connection_logger_stats._stats_logger.processed == 0
        receiver_connection_logger_stats.on_msg_processed(json_object)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.DEBUG, 'Finished processing message 1')
        assert receiver_connection_logger_stats._stats_logger.processed == 79

    @pytest.mark.asyncio
    async def test_04_on_msg_sent(self, receiver_connection_logger_stats, caplog, json_rpc_login_request_encoded,
                            debug_logging):
        assert receiver_connection_logger_stats._stats_logger.msgs.sent == 0
        receiver_connection_logger_stats.on_msg_sent(json_rpc_login_request_encoded)
        assert caplog.record_tuples == [('receiver.connection', logging.DEBUG, 'Message sent')]
        assert receiver_connection_logger_stats._stats_logger.msgs.sent == 1

    @pytest.mark.asyncio
    async def test_05_connection_finished_no_error(self, receiver_connection_logger_stats, caplog, client_sock_str,
                                             server_sock_str):
        receiver_connection_logger_stats.connection_finished()
        # noinspection PyPep8
        assert caplog.record_tuples[0] == ('receiver.connection', logging.INFO,
                                           f'TCP Server connection from {client_sock_str} to {server_sock_str} has been closed')
        assert caplog.record_tuples[1] == ('receiver.stats', logging.INFO, 'ALL')

    @pytest.mark.asyncio
    async def test_06_connection_finished_with_error(self, receiver_connection_logger_stats, zero_division_exception,
                                                     caplog, client_sock_str, server_sock_str):
        receiver_connection_logger_stats.connection_finished(zero_division_exception)
        assert caplog.record_tuples[0] == ('receiver.connection', logging.ERROR, 'division by zero')
        # noinspection PyPep8
        assert caplog.record_tuples[1] == ('receiver.connection', logging.INFO,
                                           f'TCP Server connection from {client_sock_str} to {server_sock_str} has been closed')
        assert caplog.record_tuples[2] == ('receiver.stats', logging.INFO, 'ALL')
