from dataclasses import dataclass
from .protocols import RequesterProtocol


@dataclass
class EchoRequester(RequesterProtocol):
    methods = ('echo', 'make_exception')
    notification_methods = ('request_notification',)
    last_id = 0

    def _make_request(self, method: str, request_id: bool):
        request = {'method': method}
        if request_id:
            self.last_id += 1
            request['id'] = self.last_id
        return request

    def echo(self):
        return self._make_request('echo', True)

    def make_exception(self):
        return self._make_request('echo_typo', True)

    def request_notification(self):
        return self._make_request('send_notification', False)
