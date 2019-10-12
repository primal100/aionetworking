from __future__ import annotations
import asyncio
from pathlib import Path
from ssl import SSLContext
import itertools
import os
import tempfile
import sys

from dataclasses import dataclass, field
from contextvars import ContextVar

from .base import BaseServer, BaseNetworkServer
from lib.networking.ssl import ServerSideSSL
from lib.utils import unix_address, pipe_address

import socket
from typing import List, Optional, Union


test_cv = ContextVar('test_cv', default='default')


@dataclass
class TCPServer(BaseNetworkServer):
    name = "TCP Server"
    peer_prefix = 'tcp'

    ssl: SSLContext = None
    ssl_handshake_timeout: int = None

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_server(self.protocol_factory,
                                             host=self.host, port=self.port, ssl=self.ssl,
                                             ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class UnixSocketServer(BaseServer):
    name = "Unix Socket Server"
    peer_prefix = 'unix'

    path: Union[str, Path] = field(default_factory=unix_address, metadata={'pickle': True})
    ssl: SSLContext = None
    ssl_handshake_timeout: int = None

    @property
    def listening_on(self) -> str:
        return str(self.path)

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_unix_server(self.protocol_factory, path=str(self.path), ssl=self.ssl,
                                                  ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class WindowsPipeServer(BaseServer):
    name = "Windows Named Pipe Server"
    peer_prefix = 'pipe'
    path: Union[str, Path] = field(default_factory=pipe_address, metadata={'pickle': True})

    def __post_init__(self):
        super().__post_init__()
        self.path = str(self.path).format(pid=os.getpid())

    def _print_listening_message(self) -> None:
        print(f"Serving {self.name} on {self.listening_on}")

    @property
    def listening_on(self) -> str:
        return self.path

    async def _get_server(self) -> asyncio.AbstractServer:
        servers = await self.loop.start_serving_pipe(self.protocol_factory, self.path)
        return servers[0]

    async def _stop_server(self) -> None:
        self.server.close()
        if not self.server.closed():
            await asyncio.sleep(0)

    def _is_serving(self) -> bool:
        return bool(self.server)


def pipe_server(path: Union[str, Path] = None, **kwargs):
    if hasattr(socket, 'AF_UNIX'):
        return UnixSocketServer(path=path, **kwargs)
    if sys.platform == 'win32':
        return WindowsPipeServer(path=path, **kwargs)
    raise OSError("Neither AF_UNIX nor Named Pipe is supported on this platform")


class DatagramServer(asyncio.AbstractServer):

    def __init__(self, protocol_factory, host, port, family=None, proto=None, flags=None, sock=None, start_serving=True,
                 loop=None):
        self._loop = loop
        self._sock = sock
        self._host = host
        self._port = port
        self._family = family
        self._proto = proto
        self._flags = flags
        self._protocol_factory = protocol_factory
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._protocol: Optional[asyncio.DatagramProtocol] = None
        self._serving = asyncio.Event()
        self._serve_lock = asyncio.Lock()
        self._serving_forever_fut = asyncio.Future()
        if start_serving:
            asyncio.create_task(self.start_serving())

    async def start_serving(self):
        await self._serve_lock.acquire()
        if self.is_serving():
            return
        self._transport, self._protocol = await self._loop.create_datagram_endpoint(
            self._protocol_factory, local_addr=(self._host, self._port), family=self._family,
            proto=self._proto, flags=self._flags, sock=self._sock)
        self._serving.set()
        self._serve_lock.release()

    def is_serving(self) -> bool:
        return self._serving.is_set()

    @property
    def sockets(self) -> List[socket.socket]:
        if self._serving:
            return [self._transport.get_extra_info('socket')]
        return []

    def get_loop(self):
        return self._loop

    def close(self):
        self._transport.close()
        if (self._serving_forever_fut is not None and
                not self._serving_forever_fut.done()):
            self._serving_forever_fut.cancel()
            self._serving_forever_fut = None

    async def wait_closed(self):
        return self._transport.is_closing()


@dataclass
class UDPServer(BaseNetworkServer):
    name = "UDP Server"
    peer_prefix = 'udp'

    async def _get_server(self) -> DatagramServer:
        server = DatagramServer(
            self.protocol_factory, self.host, self.port, loop=self.loop)
        await server.start_serving()
        return server
