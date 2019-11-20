from dataclasses import dataclass
from .base import BaseRequester


@dataclass
class EchoRequester(BaseRequester):
    methods = ('echo', 'make_exception')
    notification_methods = ('subscribe', 'simple')
    last_id = 0

    def _make_request(self, method: str, request_id: bool):
        request = {}
        if request_id:
            self.last_id += 1
            request['id'] = self.last_id
        request['method'] = method
        return request

    def echo(self):
        return self._make_request('echo', True)

    def simple(self):
        return self._make_request('simple', True)

    def make_exception(self):
        return self._make_request('echo_typo', True)

    def subscribe(self):
        return self._make_request('send_notification', False)
