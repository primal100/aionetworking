class TestEchoRequester:
    def test_00_send_echo(self, echo_requester, echo):
        request = echo_requester.echo()
        assert request == echo

    def test_01_send_notification(self, echo_requester, echo_notification_request):
        request = echo_requester.subscribe()
        assert request == echo_notification_request

    def test_02_make_exception(self, echo_requester, echo_exception_request):
        request = echo_requester.make_exception()
        assert request == echo_exception_request
