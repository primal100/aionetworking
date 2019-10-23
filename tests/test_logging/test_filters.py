class TestPeerFilter:
    def test_00_peer_filter_log_record_included(self, peer_filter, log_record):
        assert peer_filter.filter(log_record) is True

    def test_01_peer_filter_log_record_not_included(self, peer_filter, log_record_not_included):
        assert peer_filter.filter(log_record_not_included) is False

    def test_02_peer_filter_included(self, receiver_connection_logger, peer_filter, caplog):
        receiver_connection_logger.new_connection()
        assert len(caplog.record_tuples) == 2

    def test_03_peer_filter_not_included(self, receiver_connection_logger_wrong_peer, peer_filter, caplog):
        receiver_connection_logger_wrong_peer.new_connection()
        assert len(caplog.record_tuples) == 0


class TestMessageFilter:
    def test_00_msg_filter_log_record_included(self, message_filter, log_record_msg_object):
        assert message_filter.filter(log_record_msg_object) is True

    def test_01_msg_filter_log_record_not_included(self, message_filter, log_record_msg_object_not_included):
        assert message_filter.filter(log_record_msg_object_not_included) is False

    def test_02_msg_filter_included(self, receiver_connection_logger, message_filter, json_rpc_login_request_object,
                                    debug_logging, caplog):
        receiver_connection_logger.on_msg_decoded(json_rpc_login_request_object)
        assert len(caplog.record_tuples) == 1

    def test_03_msg_filter_not_included(self, receiver_connection_logger, message_filter,
                                        json_rpc_logout_request_object, debug_logging, caplog):
        receiver_connection_logger.on_msg_decoded(json_rpc_logout_request_object)
        assert len(caplog.record_tuples) == 0

    def test_04_msg_logger_filter_included(self, receiver_connection_logger, message_filter,
                                           json_rpc_login_request_object, debug_logging, caplog):
        json_rpc_login_request_object.logger.debug('Hello World')
        assert len(caplog.record_tuples) == 1

    def test_05_msg_logger_filter_not_included(self, receiver_connection_logger, message_filter,
                                               json_rpc_logout_request_object, debug_logging, caplog):
        json_rpc_logout_request_object.logger.debug('Hello World')
        assert len(caplog.record_tuples) == 0
