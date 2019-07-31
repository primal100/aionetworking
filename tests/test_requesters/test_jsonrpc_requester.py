import pytest
from lib.requesters.jsonrpc import MethodNotFoundError


class TestJSONRequester:
    def test_01_method_with_args(self, json_rpc_requester, json_rpc_login_request, user1):
        json_rpc_login_request.pop('id')
        json_request = json_rpc_requester.login(*user1)
        assert json_request == json_rpc_login_request

    def test_01_method_with_kwargs(self, json_rpc_requester, json_rpc_update_request, user1):
        json_rpc_update_request.pop('id')
        json_request = json_rpc_requester.update(id=0, text='Updating my first note')
        assert json_request == json_rpc_update_request

    def test_02_notification(self, json_rpc_requester, json_rpc_subscribe_request, user1):
        json_request = json_rpc_requester.subscribe_to_user(user1[0])
        assert json_request == json_rpc_subscribe_request

    def test_03_no_such_method(self, json_rpc_requester, json_rpc_update_request, user1):
        with pytest.raises(MethodNotFoundError):
            json_rpc_requester.updat(id=0, text='Updating my first note')
