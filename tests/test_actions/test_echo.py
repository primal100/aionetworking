import pytest
import json
from lib.actions.echo import InvalidRequestError
from lib.utils import aone


class TestEcho:

    @pytest.mark.asyncio
    async def test_00_do_one(self, echo_action, echo_request_object, echo_response):
        response = await echo_action.do_one(echo_request_object)
        assert response == echo_response

    @pytest.mark.asyncio
    async def test_01_do_notification(self, echo_action, echo_notification_request_object, echo_notification):
        response = await echo_action.do_one(echo_notification_request_object)
        assert response is None
        notification = await aone(echo_action.get_notifications())
        assert notification == echo_notification

    @pytest.mark.asyncio
    async def test_02_on_exception(self, echo_action, echo_exception_request_object, echo_exception_response):
        with pytest.raises(InvalidRequestError):
            await echo_action.do_one(echo_exception_request_object)
        try:
            await echo_action.do_one(echo_exception_request_object)
        except InvalidRequestError as e:
            response = echo_action.on_exception(echo_exception_request_object, e)
            assert response == echo_exception_response

    @pytest.mark.asyncio
    async def test_03_on_decode_error(self, echo_action, echo_request_invalid_json, echo_decode_error_response):
        with pytest.raises(json.decoder.JSONDecodeError):
            json.loads(echo_request_invalid_json)
        try:
            json.loads(echo_request_invalid_json)
        except json.decoder.JSONDecodeError as e:
            response = echo_action.on_decode_error(echo_request_invalid_json, e)
            assert response == echo_decode_error_response
