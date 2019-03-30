import asyncio
import datetime
import os
import struct
import re
import traceback


from typing import Sequence, List, AnyStr, Tuple, Union, NoReturn
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network


###Networking###

def supernet_of(self, other: Union[IPv4Address, IPv6Address, IPv4Network, IPv6Network]) -> bool:
    return any(n.supernet_of(other) for n in self.data)


###Future Python###

class cached_property(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    """  # noqa

    def __init__(self, func):
        self.__doc__ = getattr(func, "__doc__")
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self

        if asyncio and asyncio.iscoroutinefunction(self.func):
            return self._wrap_in_coroutine(obj)

        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value

    def _wrap_in_coroutine(self, obj):

        @asyncio.coroutine
        def wrapper():
            future = asyncio.ensure_future(self.func(obj))
            obj.__dict__[self.func.__name__] = future
            return future

        return wrapper()


class WindowsEventLoopPolicy(asyncio.DefaultEventLoopPolicy):

    # Class can be removed in Python 3.8 as ProactorEventLoop will be default for windows.

    def new_event_loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.ProactorEventLoop()


def set_loop_policy() -> NoReturn:
    if os.name == 'nt':
        asyncio.set_event_loop_policy(WindowsEventLoopPolicy())


###Logging###

def log_exception(ex: Exception) -> Sequence[str]:
        return [line.rstrip('\n') for line in
                traceback.format_exception(ex.__class__, ex, ex.__traceback__)]


###Datetime utils###

def timestamp_to_utc_string(dt) -> str:
    return datetime.datetime.strftime(dt, '%Y%m%d%H%M%S')


def now_to_utc_string() -> str:
    return timestamp_to_utc_string(datetime.datetime.now())


def datetime_to_human_readable(dt: datetime.datetime, strf: str='%Y-%m-%d %H:%M:%S.%f') -> str:
    if not dt.microsecond:
        strf = strf.replace('.%f', '')
        return dt.strftime(strf)
    return dt.strftime(strf)[:-5]


def current_date() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")


###Binary###

def pack_variable_len_string(content: bytes) -> bytes:
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
        content = path.read_bytes()
        float_size = struct.calcsize("f")
        bool_size = struct.calcsize("?")
        pos = 0
        while pos < len(content):
            sent_by_server = struct.unpack("?", content[pos:pos + bool_size])[0]
            pos += bool_size
            seconds = struct.unpack("f", content[pos:pos + float_size])[0]
            pos += float_size
            pos, peer = unpack_variable_len_string(pos, content)
            pos, packet_data = unpack_variable_len_bytes(pos, content)
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
        return struct.pack('?', sent_by_server) + struct.pack('f', seconds) + pack_variable_len_string(
            msg.sender.encode()) + pack_variable_len_string(msg.encoded)


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
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1).title()


#Text formatting
class Color:
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
    return Color.UNDERLINE + text + Color.END


###Testing###
async def run_and_wait(method, *args, interval: int=7, **kwargs):
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
    await message_manager.stop()


###ASN.1 PyCrate###
def addr_tuple_to_str(addr: Sequence):
    return ':'.join(str(a) for a in addr)


def addr_str_to_tuple(addr: AnyStr):
    return tuple(addr.split(':'))


def adapt_asn_domain(domain: Sequence) -> str:
    return '.'.join([str(x) for x in domain])


def asn_timestamp_to_utc_string(timestamp: Sequence) -> str:
    return ''.join(timestamp)


def asn_timestamp_to_datetime(timestamp: Sequence) -> datetime.datetime:
    year = int(timestamp[0] or 0)
    month = int(timestamp[1] or 0)
    day = int(timestamp[2] or 0)
    hour = int(timestamp[3] or 0)
    minute = int(timestamp[4] or 0)
    second = int(timestamp[5] or 0)
    if timestamp[6] is None:
        microsecond = 0
    else:
        microsecond = int(timestamp[6].ljust(6, '0'))
    return datetime.datetime(year, month, day, hour, minute, second, microsecond)