import asyncio
import pytest

from lib.actions.jsonrpc import InvalidParamsError, MethodNotFoundError, InvalidRequestError


class TestJsonRPC:

    def test_00_do_one(self, json_rpc_action, json_rpc_request, json_rpc_result):
        result = asyncio.run(json_rpc_action.do_one(json_rpc_request))
        assert result == json_rpc_result

    def test_01_do_one_notification(self, json_rpc_action, json_rpc_notification):
        result = asyncio.run(json_rpc_action.do_one(json_rpc_notification))
        assert result is None

    @pytest.mark.parametrize("request,exception", [
        ('json_rpc_wrong_method', MethodNotFoundError),
        ('json_rpc_invalid_params', InvalidParamsError),
        ('json_rpc_no_version', InvalidRequestError)
    ])
    def test_02_exceptions(self, json_rpc_action, request, exception):
        with pytest.raises(exception):
            asyncio.run(json_rpc_action.do_one(request))

    def test_03_filter(self, json_rpc_action, json_object):
        assert json_rpc_action.filter(json_object) is False

    def test_04_response_on_decode_error(self, json_rpc_action, json_rpc_parse_error_response):
        result = json_rpc_action.response_on_decode_error()
        assert result == json_rpc_parse_error_response

    def test_05_response_on_exception(self, json_rpc_action, json_rpc_invalid_params_response):
        result = json_rpc_action.response_on_exception(InvalidParamsError)
        assert result == json_rpc_invalid_params_response
