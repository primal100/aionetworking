import asyncio
from pathlib import Path
from ssl import SSLContext

from dataclasses import dataclass, field
import socket
import sys

from lib.networking.types import ConnectionType
from lib.networking.ssl import ClientSideSSL
from .base import BaseClient, BaseNetworkClient

from typing import Union


@dataclass
class TCPClient(BaseNetworkClient):
    name = "TCP Client"
    transport: asyncio.Transport = field(init=False, compare=False, default=None)

    #ssl: ClientSideSSL = None
    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = None

    """def __post_init__(self):
        if self.ssl and not self.ssl_context:
            self.ssl_context = self.ssl.context"""

    async def _open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_connection(
            self.protocol_factory, host=self.host, port=self.port, ssl=self.ssl_context,
            local_addr=self.local_addr, ssl_handshake_timeout=self.ssl_handshake_timeout)
        await self.conn.wait_connected()
        return self.conn


@dataclass
class UnixSocketClient(BaseClient):
    name = "Unix socket Client"
    path: Union[str, Path] = None
    transport: asyncio.Transport = field(init=False, compare=False, default=None)

    ssl_context: SSLContext = None
    ssl_handshake_timeout: int = None

    @property
    def dst(self) -> str:
        return str(self.path)

    async def _open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_unix_connection(
            self.protocol_factory, path=str(self.path), ssl=self.ssl_context,
            ssl_handshake_timeout=self.ssl_handshake_timeout)
        return self.conn


@dataclass
class WindowsPipeClient(BaseClient):
    name = "Windows Pipe Client"
    path: Union[str, Path] = None
    pid: int = None

    def __post_init__(self):
        self.path = str(self.path).format(pid=self.pid)

    @property
    def dst(self) -> str:
        return self.path

    async def _open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_pipe_connection(self.protocol_factory, self.path)
        return self.conn


def pipe_client(path: Union[str, Path] = None, **kwargs):
    if hasattr(socket, 'AF_UNIX'):
        return UnixSocketClient(path=path, **kwargs)
    if sys.platform == 'win32':
        return WindowsPipeClient(path=path, **kwargs)
    raise OSError("Neither AF_UNIX nor Named Pipe is supported on this platform")


@dataclass
class UDPClient(BaseNetworkClient):
    name = "UDP Client"
    transport: asyncio.DatagramTransport = field(init=False, compare=False, default=None)

    async def _open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_datagram_endpoint(
            self.protocol_factory, remote_addr=(self.host, self.port), local_addr=self.local_addr)
        await self.conn.wait_connected()
        return self.conn
