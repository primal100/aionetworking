from concurrent.futures import ProcessPoolExecutor
import asyncio
import socket
import multiprocessing


class ConcurrentProcess:
    def __init__(self, max_workers: int = None):
        self._loop = asyncio.get_event_loop()
        self._server_instances = []
        self._connection_instances = []
        self._connections_add_pipe_read, self._connections_add_pipe_write = self.make_reverse_channel(
            self.on_connection_details_received)
        self._connections_remove_pipe_read, self._connections_remove_pipe_write = self.make_reverse_channel(
            self.on_connection_details_received)
        self._executor = ProcessPoolExecutor(max_workers=max_workers)

    async def close(self):
        self._executor.shutdown()

    def _make_channel(self):
        return multiprocessing.Pipe(duplex=False)

    def on_connection_details_received(self):
        connections = self._connections_add_pipe_read.recv_bytes()

    def on_connection_remove_received(self):
        connections = self._connections_remove_pipe_read.recv_bytes()

    def make_reverse_channel(self, callback):
        pipe = self._make_channel()
        self._loop.add_reader(pipe, callback)
        return pipe

    async def _create_server(self, socket: socket.socket):
        pass

    async def _create_connection(self, socket: socket.socket):
        pass

    async def _new_instance(self, async_function, *args):
        await self._loop.run_in_executor(self._executor, asyncio.run, async_function, *args)

    def _create_instance_task(self, async_function, args):
        asyncio.create_task(self._new_instance(async_function, args))

    def server_instance(self, socket: socket.socket):
        self._create_instance_task(self._create_server, socket)

    def connection_instance(self): ...
