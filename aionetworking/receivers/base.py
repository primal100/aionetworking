from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field, replace

from .exceptions import ServerException
from aionetworking.compatibility_os import loop_on_close_signal, send_ready, send_stopping, send_status, send_notify_start_signal
from aionetworking.logging.loggers import get_logger_receiver
from aionetworking.networking.connections_manager import get_unique_name
from aionetworking.types.logging import LoggerType
from aionetworking.futures.value_waiters import StatusWaiter
from aionetworking.types.networking import ProtocolFactoryType
from aionetworking.utils import dataclass_getstate, dataclass_setstate, run_in_loop, addr_tuple_to_str
import sys
from .protocols import ReceiverProtocol

from aionetworking.compatibility import Protocol
from typing import Optional, Generator, List, Tuple, Callable


@dataclass
class BaseReceiver(ReceiverProtocol, Protocol):
    name = 'receiver'
    quiet: bool = False
    logger: LoggerType = field(default_factory=get_logger_receiver)
    close_tasks: List[Callable] = field(default_factory=list)
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        return dataclass_setstate(self, state)

    @run_in_loop
    async def serve_in_loop(self) -> None:
        await self.start()

    @property
    def listening_on_msgs(self) -> Generator[str, None, None]:
        yield from ()

    def send_status(self):
        msgs = ','.join(list(self.listening_on_msgs))
        if msgs:
            send_status(msgs)

    async def close(self):
        if self.close_tasks:
            await asyncio.wait([task() for task in self.close_tasks])

    async def serve_until_close_signal(self, stop_event: asyncio.Event = None,
                                       restart_event: asyncio.Event = None, notify_pid: int = None) -> None:
        stop_event = stop_event or asyncio.Event()
        restart_event = restart_event or asyncio.Event()
        loop_on_close_signal(stop_event.set, self.logger)
        await self.start()
        sys.stdout.flush()
        self.send_status()
        send_ready()
        if notify_pid:
            send_notify_start_signal(notify_pid)
        self.logger.info('Running server until signal received')
        done, pending = await asyncio.wait([stop_event.wait(), restart_event.wait()],
                                           return_when=asyncio.FIRST_COMPLETED)
        if stop_event.is_set():
            self.logger.info('Signal for stop event received')
            send_stopping()
        if restart_event.is_set():
            self.logger.info('Signal for restart event received')
        for task in pending:
            task.cancel()
        await self.close()


@dataclass
class BaseServer(BaseReceiver, Protocol):
    _serving_forever_fut = None
    name = 'Server'
    peer_prefix = 'server'

    protocol_factory:  ProtocolFactoryType = None
    server: asyncio.AbstractServer = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._full_name = get_unique_name(self.full_name)
        self.protocol_factory = replace(self.protocol_factory)
        self.protocol_factory.set_name(self._full_name, self.peer_prefix)

    @property
    @abstractmethod
    def listening_on(self) -> str: ...

    @property
    def full_name(self):
        return f"{self.name} {self.listening_on}"

    @property
    def listening_on_sockets(self) -> List[Tuple[str, int]]:
        return [socket.getsockname() for socket in self.server.sockets]

    @property
    def listening_on_msgs(self) -> Generator[str, None, None]:
        for sock_name in self.listening_on_sockets:
            if isinstance(sock_name, (tuple, list)):
                listening_on = ':'.join([str(v) for v in sock_name])
            else:
                listening_on = sock_name
            yield f"Serving {self.name} on {listening_on}"

    def _print_listening_message(self) -> None:
        for msg in self.listening_on_msgs:
            print(msg)

    async def start(self) -> None:
        if self._status.is_starting_or_started():
            raise ServerException(f"{self.name} running on {self.listening_on} already started")
        self._status.set_starting()
        await self.protocol_factory.start(logger=self.logger)
        self.logger.info('Starting %s on %s', self.name, self.listening_on)
        await self._start_server()
        if not self.quiet:
            self._print_listening_message()
        self._status.set_started()

    async def _serve_forever(self) -> None:
        if self._serving_forever_fut is not None:
            raise RuntimeError(
                f'server {self!r} is already being awaited on serve_forever()')
        if not self._status.is_starting_or_started():
            await self.start()
        self._serving_forever_fut = self.loop.create_future()

    async def serve_forever(self) -> None:
        if not self._status.is_starting_or_started():
            await self.start()
        try:
            if hasattr(self.server, 'serve_forever'):
                self._serving_forever_fut = asyncio.ensure_future(self.server.serve_forever())

            else:
                await self._serve_forever()
            try:
                await self._serving_forever_fut
            finally:
                self._serving_forever_fut = None
        except asyncio.CancelledError:
            try:
                await self.close()
            finally:
                raise

    async def close(self) -> None:
        if self._status.is_stopping_or_stopped():
            return None
        self._status.set_stopping()
        self.logger.info('Stopping %s running at %s', self.name, self.listening_on)
        if (self._serving_forever_fut is not None and
                not self._serving_forever_fut.done()):
            self._serving_forever_fut.cancel()
            self._serving_forever_fut = None
        await self._stop_server()
        await super().close()
        await self.protocol_factory.close()
        self.logger.info('%s stopped', self.name)
        self._status.set_stopped()

    def close_all_connections(self) -> None:
        self.protocol_factory.close_all_connections(None)

    async def wait_num_connections(self, num: int):
        await self.protocol_factory.wait_num_connected(num)

    async def wait_num_has_connected(self, num: int):
        await self.protocol_factory.wait_num_has_connected(num)

    async def wait_all_connections_closed(self):
        await self.protocol_factory.wait_all_closed()

    async def wait_all_tasks_done(self) -> None:
        await self.protocol_factory.close_actions()

    def is_started(self) -> bool:
        return self._status.is_started()

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped()

    def is_closed(self) -> bool:
        return self._status.is_stopped()

    async def wait_started(self):
        await self._status.wait_started()

    async def wait_has_started(self):
        await self._status.wait_has_started()

    async def wait_stopped(self):
        await self._status.wait_stopped()

    @abstractmethod
    async def _get_server(self) -> asyncio.AbstractServer: ...

    async def _start_server(self) -> None:
        self.server = await self._get_server()

    async def _stop_server(self) -> None:
        self.server.close()
        await self.server.wait_closed()


@dataclass
class BaseNetworkServer(BaseServer, Protocol):
    host: str = '0.0.0.0'
    port: int = 4000
    reuse_port: Optional[bool] = None
    backlog: int = 100
    _actual_listening_on: Optional[Tuple[str, int]] = field(default=None, init=False, repr=False)

    @property
    def listening_on(self) -> str:
        local_addr = self.actual_local_addr
        local_addr = local_addr or (self.host, self.port)
        return addr_tuple_to_str(local_addr)

    @property
    def actual_local_addr(self) -> Optional[Tuple[str, int]]:
        if self.is_started():
            self._actual_listening_on = self.listening_on_sockets[0]
            return self._actual_listening_on
        if self._actual_listening_on:
            return self._actual_listening_on
