import asyncio
from pathlib import Path
from ssl import SSLContext

from dataclasses import dataclass, field
import socket
import sys

from aionetworking.compatibility import get_client_kwargs
from aionetworking.utils import get_ip_port
from aionetworking.networking.protocol_factories import DatagramClientProtocolFactory
from aionetworking.types.networking import ConnectionType
from aionetworking.networking.ssl import ClientSideSSL
from .base import BaseClient, BaseNetworkClient

from typing import Union, Optional, List, Tuple


@dataclass
class TCPClient(BaseNetworkClient):
    name = "TCP Client"
    peer_prefix = 'tcp'
    transport: asyncio.Transport = field(init=False, compare=False, default=None)
    server_hostname: Optional[str] = None
    happy_eyeballs_delay: Optional[float] = None
    interleave: Optional[int] = None

    ssl: Optional[ClientSideSSL] = None
    ssl_handshake_timeout: Optional[int] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.ssl:
            self.ssl.set_logger(self.logger)

    @property
    def ssl_context(self) -> Optional[SSLContext]:
        if self.ssl:
            return self.ssl.context

    async def _open_connection(self) -> ConnectionType:
        extra_kwargs = get_client_kwargs(self.happy_eyeballs_delay, self.interleave)
        self.transport, self.conn = await self.loop.create_connection(
            self.protocol_factory, host=self.host, port=self.port, ssl=self.ssl_context, local_addr=self.local_addr,
            ssl_handshake_timeout=self.ssl_handshake_timeout, server_hostname=self.server_hostname, **extra_kwargs)
        return self.conn


@dataclass
class UnixSocketClient(BaseClient):
    name = "Unix Socket Client"
    peer_prefix = 'unix'
    path: Union[str, Path] = None
    transport: asyncio.Transport = field(init=False, compare=False, default=None)
    server_hostname: Optional[str] = None

    ssl: Optional[ClientSideSSL] = None
    ssl_handshake_timeout: Optional[int] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.ssl:
            self.ssl.set_logger(self.logger)

    @property
    def ssl_context(self) -> Optional[SSLContext]:
        if self.ssl:
            return self.ssl.context

    @property
    def src(self) -> str:
        if self.transport:
            _socket = self.transport.get_extra_info('socket')
            return str(_socket.fd)
        return ''

    @property
    def dst(self) -> str:
        return str(self.path)

    async def _open_connection(self) -> ConnectionType:
        self.transport, self.conn = await self.loop.create_unix_connection(
            self.protocol_factory, path=str(self.path), ssl=self.ssl_context,
            ssl_handshake_timeout=self.ssl_handshake_timeout, server_hostname=self.server_hostname)
        return self.conn


@dataclass
class WindowsPipeClient(BaseClient):
    name = "Windows Pipe Client"
    expected_connection_exceptions = (FileNotFoundError,)
    peer_prefix = 'pipe'
    path: Union[str, Path] = None
    pid: int = None

    def __post_init__(self):
        self.path = str(self.path).format(pid=self.pid)
        super().__post_init__()

    @property
    def src(self) -> str:
        return self.path

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
    peer_prefix = 'udp'
    transport: asyncio.DatagramTransport = field(init=False, compare=False, default=None)
    reuse_port: Optional[bool] = None
    allow_broadcast: Optional[bool] = None

    async def _open_connection(self) -> ConnectionType:
        protocol_factory: DatagramClientProtocolFactory
        self.transport, protocol_factory = await self.loop.create_datagram_endpoint(
            self.protocol_factory, remote_addr=(self.host, self.port), local_addr=self.local_addr,
            reuse_port=self.reuse_port, allow_broadcast=self.allow_broadcast)
        self.conn = protocol_factory.new_peer()
        await self.conn.wait_connected()
        return self.conn
