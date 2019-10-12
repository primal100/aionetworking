import asyncio
import socket
from asyncio.transports import Transport, DatagramTransport

from typing import Any


class MockAFInetSocket:
    family = socket.AF_INET


class MockAFUnixSocket:
    @property
    def family(self):
        return getattr(socket, "AF_UNIX", None)

    def fileno(self) -> int:
        return 1


class MockTransportMixin:
    _is_closing = False

    def is_closing(self) -> bool:
        return self._is_closing

    def close(self):
        self._is_closing = True


class MockTCPTransport(MockTransportMixin, Transport):

    def __init__(self, queue: asyncio.Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._peername = kwargs.get('extra', {}).get('peername')
        self.queue = queue

    def write(self, data: Any) -> None:
        if not self._is_closing:
            self.queue.put_nowait((self._peername, data))


class MockDatagramTransport(MockTransportMixin, DatagramTransport):

    def __init__(self, queue: asyncio.Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._peername = kwargs.get('extra', {}).get('peername')
        self.queue = queue

    def sendto(self, data, addr=None):
        if not self._is_closing:
            addr = addr or self._peername
            self.queue.put_nowait((addr, data))

    def abort(self):
        self.close()


class MockFileWriter:

    def __init__(self, *args, **kwargs): ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb): ...

    async def write(self, *args, **kwargs): ...

    async def flush(self, *args, **kwargs): ...

