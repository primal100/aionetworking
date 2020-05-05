import logging
import operator
import pytest
from aionetworking.utils import Expression, in_


class TestExpression:
    @pytest.mark.parametrize('attr,obj', (
            [None, False],
            ['self', False],
            ['method', True]
    ))
    def test_01_expression(self, attr, obj, json_rpc_login_request_object, json_rpc_logout_request_object):
        expr = Expression(attr, operator.eq, 'login')
        assert expr.op == operator.eq
        assert expr.case_sensitive is False
        assert expr.attr == attr
        assert expr.value == 'login'
        if obj:
            assert expr(json_rpc_login_request_object) is True
            assert expr(json_rpc_logout_request_object) is False
        else:
            assert expr('login') is True
            assert expr('logout') is False

    @pytest.mark.parametrize('expression,op,case_sensitive,attr,value,login,logout', (
                             ['method = login', operator.eq, False, 'method', 'login', True, False],
                             ['method i= Login', operator.eq, True, 'method', 'login', True, False],
                             ['method = Login', operator.eq, False, 'method', 'Login', False, False],
                             ['id = 1', operator.eq, False, 'id', '1', True, False],
                             ['id > 1', operator.gt, False, 'id', '1', False, True],
                             ['received', operator.eq, False, 'received', True, False, False],
                             ['not received', operator.eq, False, 'received', False, True, True],
                             ['method contains out', operator.contains, False, 'method', 'out', False, True],
                             ['method contains log', operator.contains, False, 'method', 'log', True, True],
                             ['method contains Out', operator.contains, False, 'method', 'Out', False, False],
                             ['method icontains Out', operator.contains, True, 'method', 'out', False, True],
                             ['method in logins', in_, False, 'method', 'logins', True, False],
                             ['method in Logins', in_, False, 'method', 'Logins', False, False],
                             ['method iin Logins', in_, True, 'method', 'logins', True, False],
    ))
    def test_01_expression_from_string(self, json_rpc_login_request_object, json_rpc_logout_request_object,
                                       expression: str, op, case_sensitive, attr, value, login, logout):
        expr = Expression.from_string(expression)
        assert expr.op.callable == op
        assert expr.case_sensitive is case_sensitive
        assert expr.attr == attr
        assert expr.value == value
        assert expr(json_rpc_login_request_object) is login
        assert expr(json_rpc_logout_request_object) is logout


class TestPeerFilter:
    def test_00_peer_filter_log_record_included(self, peer_filter, log_record):
        assert peer_filter.filter(log_record) is True

    def test_01_peer_filter_log_record_not_included(self, peer_filter, log_record_not_included):
        assert peer_filter.filter(log_record_not_included) is False

    def test_02_peer_filter_included(self, receiver_connection_logger, peer_filter, caplog):
        logging.getLogger('receiver.connection').addFilter(peer_filter)
        receiver_connection_logger.new_connection()
        assert len(caplog.record_tuples) == 2

    def test_03_peer_filter_not_included(self, receiver_connection_logger_wrong_peer, peer_filter, caplog):
        logging.getLogger('receiver.connection').addFilter(peer_filter)
        receiver_connection_logger_wrong_peer.new_connection()
        assert len(caplog.record_tuples) == 0


class TestMessageFilter:
    def test_00_msg_filter_log_record_included(self, message_filter, log_record_msg_object):
        assert message_filter.filter(log_record_msg_object) is True

    def test_01_msg_filter_log_record_not_included(self, message_filter, log_record_msg_object_not_included):
        assert message_filter.filter(log_record_msg_object_not_included) is False

    def test_02_msg_filter_included(self, receiver_connection_logger, message_filter, json_rpc_login_request_object,
                                    debug_logging, caplog):
        logging.getLogger('receiver.msg_received').addFilter(message_filter)
        receiver_connection_logger.on_msg_decoded(json_rpc_login_request_object)
        assert len(caplog.record_tuples) == 1

    def test_03_msg_filter_not_included(self, receiver_connection_logger, message_filter,
                                        json_rpc_logout_request_object, debug_logging, caplog):
        logging.getLogger('receiver.msg_received').addFilter(message_filter)
        receiver_connection_logger.on_msg_decoded(json_rpc_logout_request_object)
        assert len(caplog.record_tuples) == 0

    def test_04_msg_logger_filter_included(self, receiver_connection_logger, message_filter,
                                           json_rpc_login_request_object, debug_logging, caplog):
        logging.getLogger('receiver.msg').addFilter(message_filter)
        json_rpc_login_request_object.logger.debug('Hello World')
        assert len(caplog.record_tuples) == 1

    def test_05_msg_logger_filter_not_included(self, receiver_connection_logger, message_filter,
                                               json_rpc_logout_request_object, debug_logging, caplog):
        logging.getLogger('receiver.msg').addFilter(message_filter)
        json_rpc_logout_request_object.logger.debug('Hello World')
        assert len(caplog.record_tuples) == 0
