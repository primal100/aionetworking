import argparse
import asyncio
import gc
import concurrent.futures
import time
import socket
try:
    import uvloop
except ImportError:
    pass
import os.path
from lib.utils import run_in_loop

from socket import *


PRINT = 0


async def echo_server(loop, address, unix):
  pass


@run_in_loop
async def echo_client(address, unix):
    loop = asyncio.get_event_loop()
    if unix:
        client = socket(AF_UNIX, SOCK_STREAM)
    else:
        client = socket(AF_INET, SOCK_STREAM)
    client.connect(address)
    try:
        client.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
    except (OSError, NameError):
        pass

    with client:
        print('client connected')
        for _ in range(0, 10000):
            data=b'00'
            await loop.sock_sendall(client, data)
            data = await loop.sock_recv(client, 102400)
            if not data:
                break
    if PRINT:
        print('Connection closed')


async def echo_client_streams(reader, writer):
    sock = writer.get_extra_info('socket')
    try:
        sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
    except (OSError, NameError):
        pass
    if PRINT:
        print('Connection from', sock.getpeername())
    while True:
         data = await reader.readline()
         if not data:
             break
         writer.write(data)
    if PRINT:
        print('Connection closed')
    writer.close()


class EchoProtocol(asyncio.Protocol):
    first_msg_received = None

    def connection_made(self, transport):
        self.last_msg_received = time.time()
        print('server connected')
        self.transport = transport
        sock = transport.get_extra_info('socket')
        try:
            sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        except (OSError, NameError):
            pass

    def connection_lost(self, exc):
        print('server disconnected')
        self.transport = None
        print(self.first_msg_received)
        print(self.last_msg_received)
        time_taken = self.last_msg_received - self.first_msg_received
        print(time_taken)
        print(10000 /time_taken)

    def data_received(self, data):
        if not self.first_msg_received:
            self.first_msg_received = time.time()
        self.transport.write(data)
        self.last_msg_received = time.time()


async def print_debug(loop):
    while True:
        print(chr(27) + "[2J")  # clear screen
        loop.print_debug_info()
        await asyncio.sleep(0.5, loop=loop)


async def run_client(address, unix):
    await asyncio.sleep(1)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        num_clients = 1
        coros = []
        for i in range(0, num_clients):
            coro = loop.run_in_executor(executor, echo_client, address, unix)
            coros.append(coro)
        await asyncio.wait(coros)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--uvloop', default=False, action='store_true')
    parser.add_argument('--streams', default=False, action='store_true')
    parser.add_argument('--proto', default=False, action='store_true')
    parser.add_argument('--addr', default='127.0.0.1:25000', type=str)
    parser.add_argument('--print', default=False, action='store_true')
    args = parser.parse_args()

    if args.uvloop:
        loop = uvloop.new_event_loop()
        print('using UVLoop')
    else:
        loop = asyncio.new_event_loop()
        print('using asyncio loop')

    asyncio.set_event_loop(loop)
    loop.set_debug(False)

    if args.print:
        PRINT = 1

    if hasattr(loop, 'print_debug_info'):
        loop.create_task(print_debug(loop))
        PRINT = 0

    unix = False
    if args.addr.startswith('file:'):
        unix = True
        addr = args.addr[5:]
        if os.path.exists(addr):
            os.remove(addr)
    else:
        addr = args.addr.split(':')
        addr[1] = int(addr[1])
        addr = tuple(addr)

    print('serving on: {}'.format(addr))

    if args.streams:
        if args.proto:
            print('cannot use --stream and --proto simultaneously')
            exit(1)

        print('using asyncio/streams')
        if unix:
            coro = asyncio.start_unix_server(echo_client_streams,
                                             addr, loop=loop,
                                             limit=1024 * 1024)
        else:
            coro = asyncio.start_server(echo_client_streams,
                                        *addr, loop=loop,
                                        limit=1024 * 1024)
        srv = loop.run_until_complete(coro)
    elif args.proto:
        if args.streams:
            print('cannot use --stream and --proto simultaneously')
            exit(1)

        print('using simple protocol')
        if unix:
            coro = loop.create_unix_server(EchoProtocol, addr)
        else:
            coro = loop.create_server(EchoProtocol, *addr)
        srv = loop.run_until_complete(coro)
    else:
        print('using sock_recv/sock_sendall')
        loop.create_task(echo_server(loop, addr, unix))
        loop.create_task(run_client(addr, unix))
    try:
        loop.run_until_complete(run_client(addr, unix))
    finally:
        if hasattr(loop, 'print_debug_info'):
            gc.collect()
            print(chr(27) + "[2J")
            loop.print_debug_info()

        loop.close()