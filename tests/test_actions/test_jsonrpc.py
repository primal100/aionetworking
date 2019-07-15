import pytest
from json.decoder import JSONDecodeError

from lib.actions.jsonrpc import InvalidParamsError, MethodNotFoundError, InvalidRequestError


class TestJsonRPC:

    @pytest.mark.asyncio
    async def test_00_do_one(self, json_rpc_action, json_object, json_rpc_result):
        result = await json_rpc_action.do_one(json_object)
        assert result == json_rpc_result

    @pytest.mark.asyncio
    async def test_01_do_one_notification(self, json_rpc_action, json_rpc_notification_object):
        result = await json_rpc_action.do_one(json_rpc_notification_object)
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("json_rpc_error_request,exception", [
        ('no_version', InvalidRequestError),
        ('wrong_method', MethodNotFoundError),
        ('invalid_params', InvalidParamsError),
    ], indirect=['json_rpc_error_request'])
    async def test_02_exceptions(self, json_rpc_action, json_codec, json_rpc_error_request, exception):
        json_obj = json_codec.from_decoded(json_rpc_error_request)
        with pytest.raises(exception):
            await json_rpc_action.do_one(json_obj)

    def test_03_filter(self, json_rpc_action, json_object):
        assert json_rpc_action.filter(json_object) is False

    def test_04_response_on_decode_error(self, json_rpc_action, invalid_json, json_rpc_parse_error_response):
        result = json_rpc_action.response_on_decode_error(invalid_json, JSONDecodeError)
        assert result == json_rpc_parse_error_response

    @pytest.mark.parametrize("json_rpc_error_request,json_rpc_error_response, exception", [
        ('no_version', 'no_version', InvalidRequestError),
        ('wrong_method', 'wrong_method', MethodNotFoundError),
        ('invalid_params', 'invalid_params', InvalidParamsError),
    ], indirect=['json_rpc_error_request', 'json_rpc_error_response'])
    def test_05_response_on_exception(self, json_rpc_action, json_codec, json_rpc_error_request, json_rpc_error_response, exception):
        obj = json_codec.from_decoded(json_rpc_error_request)
        result = json_rpc_action.response_on_exception(obj, exception())
        assert result == json_rpc_error_response
