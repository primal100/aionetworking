from __future__ import annotations
import asyncio
from aiofiles.os import wrap
from collections import ChainMap
from ipaddress import AddressValueError
import builtins
import datetime
import io
import operator
import os
import struct
import re
import traceback
import time
import itertools
import sys
import socket
import tempfile
from dataclasses import dataclass, fields, MISSING
from functools import wraps

from .compatibility import Protocol
from pathlib import Path
from typing import Sequence, Callable, List, AnyStr, Tuple, Union, Iterator, AsyncGenerator, Any, TYPE_CHECKING, Generator, Iterable
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network

try:
    import psutil
    supports_system_info = True
except ImportError:
    psutil = None
    supports_system_info = False


str_to_list = re.compile(r"^\s+|\s*,\s*|\s+$")


###Coroutines###
arename = wrap(os.rename)
aremove = wrap(os.remove)
amkdir = wrap(os.mkdir)
armdir = wrap(os.rmdir)


async def time_coro(coro):
    start_time = time.time()
    await coro
    return time.time() - start_time


###Coroutines###
async def benchmark(async_func: Callable, *args, num_times: int = 5, quiet: bool = False, cleanup: Callable = None,
                    cleanup_args=(), num_items: int = None, num_bytes: int = None, ignore_first: bool = True, **kwargs):
    times = []
    if not quiet:
        print("Running", async_func.__name__)
    total = 0
    if ignore_first:
        await time_coro(async_func(*args, **kwargs))
        if cleanup:
            await cleanup(*cleanup_args)
    for _ in range(0, num_times):
        time_taken = await time_coro(async_func(*args, **kwargs))
        if cleanup:
            await cleanup(*cleanup_args)
        times.append(str(time_taken))
        total += time_taken
        if not quiet:
            print(time_taken)
    average = total / num_times
    if not quiet:
        print("Average time taken:", average)
        if num_items:
            average_per_item = average / num_items
            items_per_second = 1 / average_per_item
            print('Num Items:', num_items)
            print("Average per item:", average_per_item)
            print("Items per second:", items_per_second)
            if num_bytes:
                print("Bytes per second:", (num_bytes / average))
                times = '\t'.join(times)
                print(f"{async_func.__name__}\t{num_bytes}\t{num_items}\t{times}")


###Dataclasses###
def compare_dataclasses(dc1, dc2) -> Generator[str, None, None]:
    for f in fields(dc1):
        value1 = getattr(dc1, f.name)
        value2 = getattr(dc2, f.name)
        if  value1 != value2:
            if f.compare:
                yield f.name, value1, value2


###Typing###
class EmptyProtocol(Protocol):
    pass


def inherit_on_type_checking_only(arg):
    """Decorator for protocols/ABC classes who's methods can be used for
    type checking on subclasses but are not available at runtime.
    Used to add type hints for dynamic attributes (__getattr__, etc)
    """
    if TYPE_CHECKING:
        return arg
    return EmptyProtocol


###Iterators###
"""def has_items(generator: Iterator) -> bool:
    try:
        next(generator)
        return True
    except StopIteration:
        return False"""


###Async Generators###
async def aone(generator: AsyncGenerator) -> Any:
    item = await generator.__anext__()
    await generator.aclose()
    return item


async def anext(generator: AsyncGenerator) -> Any:
    return await generator.__anext__()


async def alist(generator: AsyncGenerator) -> List[Any]:
    return [i async for i in generator]


###Asyncio###

def run_in_loop(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        return asyncio.run(f(*args, **kwds))

    return wrapper


def set_proactor_loop_policy_windows() -> None:
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def set_selector_loop_policy_windows() -> None:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def set_selector_loop_policy_linux() -> None:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


def set_uvloop_policy_linux() -> None:
    import uvloop
    uvloop.install()


def set_loop_policy(linux_loop_type: str = None, windows_loop_type: str = None) -> None:
    if os.name == 'posix':
        if linux_loop_type == 'selector':
            set_selector_loop_policy_linux()
        elif linux_loop_type == 'uvloop':
            set_uvloop_policy_linux()
    elif os.name == 'nt':
        if windows_loop_type == 'selector':
            set_selector_loop_policy_windows()
        elif windows_loop_type == 'proactor':
            set_proactor_loop_policy_windows()


###Logging###

def log_exception(ex: BaseException) -> Sequence[str]:
        return [line.rstrip('\n') for line in
                traceback.format_exception(ex.__class__, ex, ex.__traceback__)]


###Datetime utils###

"""def timestamp_to_utc_string(dt) -> str:
    return datetime.datetime.strftime(dt, '%Y%m%d%H%M%S')


def now_to_utc_string() -> str:
    return timestamp_to_utc_string(datetime.datetime.now())


def datetime_to_human_readable(dt: datetime.datetime, strf: str='%Y-%m-%d %H:%M:%S.%f') -> str:
    if not dt.microsecond:
        strf = strf.replace('.%f', '')
        return dt.strftime(strf)
    return dt.strftime(strf)[:-5]


def current_date() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")"""


###Multiprocessing###

_mmap_counter = itertools.count()


def arbitrary_address(family, future_pid=False) -> Union[Tuple[str, int], Path]:
    if family == 'AF_INET':
        return 'localhost', 0
    if family == 'AF_UNIX':
        return Path(tempfile.mktemp(prefix='listener-', dir=tempfile.mkdtemp(prefix='pymp-')))
    if family == 'AF_PIPE':
        pid = '{pid}' if future_pid else os.getpid()
        return Path(tempfile.mktemp(prefix=r'\\.\pipe\pyc-%d-%d-' %
                               (pid, next(_mmap_counter)), dir=""))
    raise ValueError('unrecognized family')


def unix_address() -> Path:
    return arbitrary_address('AF_UNIX')


def pipe_address() -> Path:
    return arbitrary_address('AF_PIPE')


def pipe_address_by_os() -> Path:
    if hasattr(socket, 'AF_UNIX'):
        return unix_address()
    if sys.platform == 'win32':
        return pipe_address()
    OSError("Neither AF_UNIX nor Named Pipe is supported on this platform")


###Binary###

"""def pack_variable_len_string(content: bytes) -> bytes:
    return struct.pack("I", len(content)) + content


def unpack_variable_len_bytes(pos: int, content: bytes) -> (int, bytes):
    int_size = struct.calcsize("I")
    length = struct.unpack("I", content[pos:pos + int_size])[0]
    pos += int_size
    end_byte = pos + length
    data = content[pos:end_byte]
    return end_byte, data


def unpack_variable_len_string(*args) -> (int, str):
    end_byte, data = unpack_variable_len_bytes(*args)
    return end_byte, data.decode()


def unpack_variable_len_strings(content: bytes) -> List[AnyStr]:
    pos = 0
    bytes_list = []
    while pos < len(content):
        pos, string = unpack_variable_len_string(pos, content)
        bytes_list.append(string)
    return bytes_list


###Recording###

class Record:
    first_msg_time = 0

    @classmethod
    def from_file(cls, path):
        if isinstance(path, io.BufferedReader):
            content = path.read()
        else:
            content = path.read_bytes()
        float_size = struct.calcsize("f")
        bool_size = struct.calcsize("?")
        pos = 0
        while pos < len(content):
            sent_by_server = struct.unpack("?", content[pos:pos + bool_size])[0]
            pos += bool_size
            seconds = struct.unpack("f", content[pos:pos + float_size])[0]
            pos += float_size
            is_bytes = struct.unpack("?", content[pos:pos + bool_size])[0]
            pos += bool_size
            pos, peer = unpack_variable_len_string(pos, content)
            pos, packet_data = unpack_variable_len_bytes(pos, content)
            if not is_bytes:
                packet_data = packet_data.decode()
            yield ({'sent_by_server': sent_by_server,
                    'seconds': seconds,
                    'peer': peer,
                    'data': packet_data})

    def pack_server_msg(self, msg):
        return self.pack_recorded_packet(True, msg)

    def pack_client_msg(self, msg):
        return self.pack_recorded_packet(False, msg)

    def pack_recorded_packet(self, sent_by_server: bool, msg) -> bytes:
        if self.first_msg_time:
            time_delta = msg.received_timestamp - self.first_msg_time
            seconds = time_delta.seconds + round(time_delta.microseconds / 1000000)
        else:
            self.first_msg_time = msg.received_timestamp
            seconds = 0
        if isinstance(msg.encoded, bytes):
            is_bytes = True
            encoded = msg.encoded
        else:
            is_bytes = False
            encoded = msg.encoded.encode()
        return struct.pack('?', sent_by_server) + struct.pack('f', seconds) + struct.pack('?', is_bytes) + pack_variable_len_string(
            msg.sender.encode()) + pack_variable_len_string(encoded)


def unpack_recorded_packets(content: bytes) -> Sequence[Tuple[int, AnyStr, bytes]]:
    int_size = struct.calcsize("I")
    pos = 0
    packets = []
    while pos < len(content):
        seconds = struct.unpack("I", content[pos:pos+int_size])[0]
        pos += int_size
        pos, sender = unpack_variable_len_string(pos, content)
        pos, packet_data = unpack_variable_len_string(pos, content)
        packets.append((seconds, sender, packet_data))
    return packets

#Text
def camel_case_to_title(string: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', string)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1).title()"""


#Text formatting
"""class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def bold(text: str) -> str:
    return Color.BOLD + text + Color.END


def underline(text: str) -> str:
    return Color.UNDERLINE + text + Color.END"""


###Testing###
"""async def run_and_wait(method, *args, interval: int=7, **kwargs):
    await method(*args, **kwargs)
    await asyncio.sleep(interval)


async def run_wait_close(method, message_manager, *args, interval: int=1, **kwargs):
    await run_and_wait(method, *args, interval=interval, **kwargs)
    await message_manager.stop()


async def run_wait_close_multiple(method, message_manager, sender, msgs: [Sequence],
                                  interval: int=1, final_interval: int=5, **kwargs):
    for message in msgs:
        await run_and_wait(method, sender, message, interval=interval, **kwargs)
    await asyncio.sleep(final_interval)
    await message_manager.stop()"""


def addr_tuple_to_str(addr: Sequence):
    return ':'.join(str(a) for a in addr)


def addr_str_to_tuple(addr: AnyStr):
    addr, port = addr.split(':')
    return addr, int(port)


def dataclass_getstate(self):
    state = {}
    f = fields(self)
    for field in f:
        name = field.name
        if field.init:
            try:
                value = getattr(self, field.name)
                if field.default == MISSING and field.default_factory == MISSING:
                    state[name] = value
                elif field.default != MISSING and value != field.default:
                    if field.metadata.get('pickle', True):
                        state[name] = value
                elif field.default_factory != MISSING:
                    if field.metadata.get('pickle', False):
                        state[name] = value
            except AttributeError:
                pass
    return state


def dataclass_setstate(self, state):
    self.__dict__.update(self.__class__(**state).__dict__)


class SystemInfo:
    @property
    def memory(self):
        try:
            return psutil.Process(os.getpid()).memory_info()[0]/2.**30
        except NameError:
            return "Unknown"

    @property
    def cpu(self):
        try:
            return psutil.Process(os.getpid()).cpu_percent()
        except NameError:
            return "Unknown"


class IPNetwork:
    def __init__(self, network: Union[str, IPv4Network, IPv6Network]):
        if isinstance(network, IPv4Network):
            self.ip_network = network
            self.is_ipv6 = False
        elif isinstance(network, IPv6Network):
            self.ip_network = network
            self.is_ipv6 = True
        else:
            try:
                self.ip_network = IPv4Network(network)
                self.is_ipv6 = False
            except AddressValueError:
                try:
                    self.ip_network = IPv6Network(network)
                    self.is_ipv6 = True
                except AddressValueError:
                    raise AddressValueError(f'{network} is not valid IPv4 or IPv6 network')

    def __eq__(self, other):
        return self.ip_network == other.ip_network

    def supernet_of(self, network: Union[IPv4Network, IPv6Network]):
        return self.ip_network.supernet_of(network)


def supernet_of(network: Union[str, IPNetwork, IPv4Network, IPv6Network], networks: Sequence[IPNetwork]):
    if not isinstance(network, IPNetwork):
        network = IPNetwork(network)
    if network.is_ipv6:
        networks = filter(lambda n: n.is_ipv6, networks)
    else:
        networks = filter(lambda n: not n.is_ipv6, networks)
    return any(n.supernet_of(network.ip_network) for n in networks)


@dataclass
class CallableFromString(Callable):
    _strings_to_callables = {}
    callable: Callable

    def __post_init__(self):
        self.callable = self.adapt_callable(self.callable)

    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)

    def adapt_callable(self, v: Union[str, Callable]):
        if isinstance(v, str):
            try:
                return self._strings_to_callables[v]
            except KeyError:
                raise TypeError(f"{v} not found")
        if v not in self._strings_to_callables.values():
            name = self.__class__.__name__
            raise TypeError(f"{v} not a valid {name}")
        return v


class Builtin(CallableFromString):
    _strings_to_callables = ChainMap(builtins.__dict__, {'istr': str})


def in_(a, b) -> bool:
    return a in b


class Operator(CallableFromString):
    _strings_to_callables = {
        '=': operator.eq,
        '==': operator.eq,
        'eq': operator.eq,
        '<': operator.lt,
        'lt': operator.lt,
        '<=': operator.le,
        'lte': operator.le,
        '!<': operator.ne,
        'ne': operator.ne,
        '>': operator.gt,
        'gt': operator.gt,
        '>=': operator.ge,
        'ge': operator.ge,
        'in': in_,
        'contains': operator.contains
    }


@dataclass
class Expression:
    attr: str
    op: Operator
    value_type: Builtin
    value: Any
    case_sensitive: bool = True

    @classmethod
    def from_string(cls, string: str):
        attr, op, value_type, value = string.split()
        if op.startswith('i'):
            case_sensitive = True
            op = op.split('i')[1]
        else:
            case_sensitive = False
        op = Operator(op)
        return cls(attr, op, value_type, value, case_sensitive=case_sensitive)

    def __call__(self, obj: Any) -> bool:
        if not self.attr or self.attr == 'self':
            value = obj
        else:
            value = getattr(obj, self.attr)
        if self.case_sensitive:
            if isinstance(value, Iterable):
                value = [v.lower() for v in value]
            else:
                value = value.lower()
            return self.op(value, self.value.lower())
        return self.op(value, self.value)