from __future__ import annotations
import asyncio
from pathlib import Path
from ssl import SSLContext
import itertools
import os
import tempfile
import sys

from dataclasses import dataclass, field

from .base import BaseServer, BaseNetworkServer
from lib.networking.ssl import ServerSideSSL
from lib.utils import unix_address, pipe_address

import socket
from typing import List, Optional, Union


@dataclass
class TCPServer(BaseNetworkServer):
    name = "TCP Server"

    ssl: ServerSideSSL = None
    ssl_handshake_timeout: int = None

    def __post_init__(self):
        if isinstance(self.ssl, SSLContext):
            self.ssl = ServerSideSSL(context=self.ssl)

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_server(self.protocol_factory,
                                             host=self.host, port=self.port, ssl=self.ssl.context,
                                             ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class UnixSocketServer(BaseServer):
    name = "Unix Socket Server"

    path: Union[str, Path] = field(default_factory=unix_address)
    ssl: ServerSideSSL = None
    ssl_handshake_timeout: int = None

    @property
    def listening_on(self) -> str:
        return str(self.path)

    def __post_init__(self):
        if isinstance(self.ssl, SSLContext):
            self.ssl = ServerSideSSL(context=self.ssl)

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_unix_server(self.protocol_factory, path=str(self.path), ssl=self.ssl.context,
                                                  ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class WindowsPipeServer(BaseServer):
    name = "Windows Named Pipe Server"
    path: Union[str, Path] = field(default_factory=pipe_address)

    def __post_init__(self):
        self.path = str(self.path).format(pid=os.getpid())

    @property
    def listening_on(self) -> str:
        return self.path

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.start_serving_pipe(self.protocol_factory, self.path)[0]


def unix_or_windows_server(address: Union[str, Path] = None, **kwargs):
    if hasattr(socket, 'AF_UNIX'):
        return UnixSocketServer(path=address, **kwargs)
    if sys.platform == 'win32':
        return WindowsPipeServer(path=address, **kwargs)
    raise OSError("Neither AF_UNIX nor Named Pipe is supported on this platform")


class _DatagramServer(asyncio.AbstractServer):
    is_serving: bool = False

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
        self._serving = False
        if start_serving:
            asyncio.create_task(self.start_serving())

    async def start_serving(self):
        if self._serving:
            return
        self._transport, self._protocol = await self._loop.create_datagram_endpoint(
            self._protocol_factory, local_addr=(self._host, self._port), family=self._family,
            proto=self._proto, flags=self._flags, sock=self._sock)
        self._serving = True

    @property
    def sockets(self) -> List[socket.socket]:
        if self._serving:
            return [self._transport.get_extra_info('socket')]
        return []

    def get_loop(self):
        return self._loop

    def close(self):
        self._transport.close()

    async def wait_closed(self):
        return self._transport.is_closing()


@dataclass
class UDPServer(BaseNetworkServer):
    name = "UDP Server"

    async def _get_server(self) -> _DatagramServer:
        server = _DatagramServer(
            self.protocol_factory, self.host, self.port, loop=self.loop)
        await server.start_serving()
        return server
