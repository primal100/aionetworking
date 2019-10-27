from __future__ import annotations
import asyncio
from pathlib import Path
from ssl import SSLContext
import os
import sys

from dataclasses import dataclass, field
from contextvars import ContextVar

from .base import BaseServer, BaseNetworkServer
from aionetworking.networking.connections import UDPServerConnection
from aionetworking.networking.protocol_factories import DatagramServerProtocolFactory, StreamServerProtocolFactory
from aionetworking.networking.ssl import ServerSideSSL
from aionetworking.utils import unix_address, pipe_address
from aionetworking.futures.value_waiters import StatusWaiter

import socket
from typing import List, Optional, Union


test_cv = ContextVar('test_cv', default='default')


@dataclass
class TCPServer(BaseNetworkServer):
    name = "TCP Server"
    peer_prefix = 'tcp'
    protocol_factory: StreamServerProtocolFactory = None

    ssl: ServerSideSSL = None
    ssl_handshake_timeout: int = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.ssl:
            self.ssl.set_logger(self.logger)

    @property
    def ssl_context(self) -> Optional[SSLContext]:
        if self.ssl:
            return self.ssl.context

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_server(self.protocol_factory,
                                             host=self.host, port=self.port, ssl=self.ssl_context,
                                             ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class UnixSocketServer(BaseServer):
    name = "Unix Socket Server"
    peer_prefix = 'unix'
    protocol_factory: StreamServerProtocolFactory = None

    path: Union[str, Path] = field(default_factory=unix_address, metadata={'pickle': True})
    ssl: ServerSideSSL = None
    ssl_handshake_timeout: int = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.ssl:
            self.ssl.set_logger(self.logger)

    @property
    def ssl_context(self) -> Optional[SSLContext]:
        if self.ssl:
            return self.ssl.context

    @property
    def listening_on(self) -> str:
        return str(self.path)

    async def _get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_unix_server(self.protocol_factory, path=str(self.path), ssl=self.ssl_context,
                                                  ssl_handshake_timeout=self.ssl_handshake_timeout)


@dataclass
class WindowsPipeServer(BaseServer):
    name = "Windows Named Pipe Server"
    peer_prefix = 'pipe'
    path: Union[str, Path] = field(default_factory=pipe_address, metadata={'pickle': True})
    protocol_factory: StreamServerProtocolFactory = None

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

    def __init__(self, protocol_factory: DatagramServerProtocolFactory, host: str, port: int,
                 family: int = 0, proto: int = 0, flags: int = 0, sock = None, start_serving: bool=True,
                 reuse_address: bool = None, reuse_port: bool = None, allow_broadcast: bool = None, loop = None):
        self._loop = loop or asyncio.get_event_loop()
        self._sock = sock
        self._host = host
        self._port = port
        self._family = family
        self._proto = proto
        self._flags = flags
        self._reuse_address = reuse_address
        self._reuse_port = reuse_port
        self._allow_broadcast = allow_broadcast
        self._protocol_factory = protocol_factory
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._protocol: Optional[UDPServerConnection] = None
        self._status = StatusWaiter()
        if start_serving:
            asyncio.create_task(self.start_serving())
            self._status.set_starting()

    async def start_serving(self):
        if self.is_serving():
            return
        self._transport, self._protocol = await self._loop.create_datagram_endpoint(
            self._protocol_factory, local_addr=(self._host, self._port), family=self._family,
            allow_broadcast=self._allow_broadcast, proto=self._proto, flags=self._flags, sock=self._sock,
            reuse_address=self._reuse_address, reuse_port=self._reuse_port)
        self._status.set_started()

    async def wait_started(self):
        await self._status.wait_started()

    def is_serving(self) -> bool:
        return self._status.is_started()

    @property
    def sockets(self) -> List[socket.socket]:
        if self._transport:
            return [self._transport.get_extra_info('socket')]
        return []

    def get_loop(self):
        return self._loop

    def _set_stopped(self, task: asyncio.Task):
        if task.exception():
            raise task.exception()
        self._status.set_stopped()

    def close(self):
        self._transport.close()
        self._status.set_stopped()

    async def wait_closed(self):
        await self._status.wait_stopped()


@dataclass
class UDPServer(BaseNetworkServer):
    protocol_factory: DatagramServerProtocolFactory = None
    name = "UDP Server"
    peer_prefix = 'udp'

    async def _get_server(self) -> DatagramServer:
        server = DatagramServer(
            self.protocol_factory, self.host, self.port, loop=self.loop)
        await server.wait_started()
        return server
