from __future__ import annotations
import asyncio
from aiofiles.os import wrap
from collections import ChainMap
from ipaddress import AddressValueError
import builtins
import operator
import os
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
from typing import Sequence, Callable, List, AnyStr, Tuple, Union, AsyncGenerator, Any, TYPE_CHECKING, Generator, Iterable
from ipaddress import IPv4Network, IPv6Network

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


###Networking###

def addr_tuple_to_str(addr: Sequence):
    return ':'.join(str(a) for a in addr)


def addr_str_to_tuple(addr: AnyStr):
    addr, port = addr.split(':')
    return addr, int(port)


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


###System###

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


###Misc###

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