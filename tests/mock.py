from asyncio.transports import Transport, DatagramTransport
import collections

from typing import Any


class MockTransportMixin:
    _is_closing = False

    def is_closing(self) -> bool:
        return self._is_closing

    def close(self):
        self._is_closing = True


class MockTCPTransport(MockTransportMixin, Transport):

    def __init__(self, deque: collections.deque, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._peername = kwargs.get('extra', {}).get('peername')
        self.queue = deque

    def write(self, data: Any) -> None:
        if not self._is_closing:
            self.queue.append((self._peername, data))


class MockDatagramTransport(MockTransportMixin, DatagramTransport):

    def __init__(self, deque: collections.deque, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._peername = kwargs.get('extra', {}).get('peername')
        self.queue = deque

    def sendto(self, data, addr=None):
        if not self._is_closing:
            addr = addr or self._peername
            self.queue.append((addr, data))

    def abort(self):
        self.close()




