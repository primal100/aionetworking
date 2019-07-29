import pytest
import asyncio
import json
from json.decoder import JSONDecodeError

from lib.actions.jsonrpc import InvalidParamsError, MethodNotFoundError, InvalidRequestError
from lib.actions.contrib.jsonrpc_crud import AuthenticationError, PermissionsError
from lib.formats.contrib.types import JSONObjectType


class TestJsonRPC:

    @pytest.mark.asyncio
    async def test_00_login(self, json_rpc_action, json_rpc_login_request_object,
                            json_rpc_login_response, context, user1_context):
        result = await json_rpc_action.async_do_one(json_rpc_login_request_object)
        assert result == json_rpc_login_response
        assert context == user1_context

    @pytest.mark.parametrize(['json_rpc_object_no_user', 'exception'],
                             [
                              ['json_rpc_create_request', PermissionsError],
                              ['json_rpc_login_wrong_password', AuthenticationError]
                              ],
                             indirect=['json_rpc_object_no_user'])
    @pytest.mark.asyncio
    async def test_01_not_logged_in(self, json_rpc_action, json_rpc_object_no_user: JSONObjectType, exception,
                                    json_rpc_app, default_notes):
        with pytest.raises(exception):
            await json_rpc_action.async_do_one(json_rpc_object_no_user)
        assert json_rpc_app.notes == default_notes

    @pytest.mark.asyncio
    @pytest.mark.parametrize(['json_rpc_object_user1', 'response', 'notification', 'items'],
                             [
                                ['json_rpc_create_request', 'json_rpc_create_response', 'json_rpc_create_notification', 'after_create_notes'],
                                 #['json_rpc_update_request', 'json_rpc_update_response', 'json_rpc_update_notification', 'after_update_notes'],
                                 #['json_rpc_delete_request', 'json_rpc_delete_response', 'json_rpc_delete_notification', {}],
                                 #['json_rpc_get_request', 'json_rpc_get_response', None, 'default_notes'],
                                 #['json_rpc_logout_request', 'json_rpc_logout_response', None, 'default_notes']
                              ],
                             indirect=True)
    async def test_03_logged_in_crud_logout(self, json_rpc_action, json_rpc_app, connections_manager_with_connection, simple_network_connection,
                                            json_rpc_object_user1: JSONObjectType, response, notification, items, deque, subscribe_key):
        connections_manager_with_connection.subscribe(simple_network_connection.peer_str, subscribe_key)
        assert connections_manager_with_connection.is_subscribed(simple_network_connection, subscribe_key)
        result = await json_rpc_action.async_do_one(json_rpc_object_user1)
        assert result == response
        assert json_rpc_app.notes == items
        await asyncio.wait_for(json_rpc_action.close(), timeout=1)
        if notification:
            item = deque.pop()
            assert item == notification

    @pytest.mark.asyncio
    @pytest.mark.parametrize(['json_rpc_object_user2', 'exception'],
                             [
                                 ['json_rpc_delete_request', PermissionsError],
                                 ['json_rpc_invalid_params_request', InvalidParamsError],
                                 ['json_rpc_wrong_method_request', MethodNotFoundError],
                                 ['json_rpc_get_request_no_object', KeyError],
                              ],
                             indirect=['json_rpc_object_user2'])
    async def test_04_tasks_with_exception(self, json_rpc_action, json_rpc_app,
                                           json_rpc_object_user2: JSONObjectType, exception, default_notes):
        with pytest.raises(exception):
            result = await json_rpc_action.async_do_one(json_rpc_object_user2)
        assert json_rpc_app.notes == default_notes
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(json_rpc_action._notifications_queue.get(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_05_subscribe_unsubscribe(self, json_rpc_action, json_rpc_app,
                                            json_rpc_subscribe_request_object, json_rpc_unsubscribe_request_object,
                                            connections_manager_with_connection, peer_str, subscribe_key):
        result = await json_rpc_action.async_do_one(json_rpc_subscribe_request_object)
        assert result is None
        assert connections_manager_with_connection.peer_is_subscribed(peer_str, subscribe_key)
        result = await json_rpc_action.async_do_one(json_rpc_unsubscribe_request_object)
        assert not connections_manager_with_connection.peer_is_subscribed(peer_str, subscribe_key)

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
        try:
            result = json.loads(invalid_json)
        except JSONDecodeError as e:
            result = json_rpc_action.response_on_decode_error(invalid_json, e)
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
