import datetime
import os
import struct
import re
import asyncio
import traceback

from pathlib import Path

from typing import Sequence, Mapping, AnyStr, Tuple

def set_loop():
    if os.name == 'nt':
        # Following two lines can be removed in Python 3.8 as ProactorEventLoop will be default for windows.
        import asyncio
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)


def log_exception(ex):
        return [line.rstrip('\n') for line in
                traceback.format_exception(ex.__class__, ex, ex.__traceback__)]


def timestamp_to_utc_string(dt) -> str:
    return datetime.datetime.strftime(dt, '%Y%m%d%H%M%S')


def now_to_utc_string() -> str:
    return timestamp_to_utc_string(datetime.datetime.now())


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


def datetime_to_human_readable(dt: datetime.datetime, strf: str='%Y-%m-%d %H:%M:%S.%f') -> str:
    if not dt.microsecond:
        strf = strf.replace('.%f', '')
        return dt.strftime(strf)
    return dt.strftime(strf)[:-5]


def current_date() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")


def adapt_asn_domain(domain: Sequence) -> str:
    return '.'.join([str(x) for x in domain])


def write_to_files(base_path: Path, write_mode: str, file_writes: Mapping[Path, AnyStr]):
    """
    Takes a dictionary containing filepaths (keys) and data to write to each one (values)
    """
    for file_name in file_writes.keys():
        file_path = base_path.joinpath(file_name)
        with file_path.open(write_mode) as f:
            f.write(file_writes[file_name])


def pack_variable_len_string(content:bytes) -> bytes:
    return struct.pack("I", len(content)) + content


def unpack_variable_len_string(pos: int, content: bytes) -> (int, bytes):
    int_size = struct.calcsize("I")
    length = struct.unpack("I", content[pos:pos + int_size])[0]
    pos += int_size
    end_byte = pos + length
    data = content[pos:end_byte]
    return end_byte, data


def unpack_variable_len_strings(content: bytes) -> Sequence[bytes]:
    pos = 0
    bytes_list = []
    while pos < len(content):
        pos, string = unpack_variable_len_string(pos, content)
        bytes_list.append(string)
    return bytes_list


def pack_recorded_packet(sender: AnyStr, msg: bytes, seconds: int) -> bytes:
    return struct.pack('I', seconds) + pack_variable_len_string(
            sender.encode()) + pack_variable_len_string(msg)


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


def camel_case_to_title(string: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', string)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1).title()


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


def store_dicts(dicts: Sequence[Mapping]) -> str:
    text = ""
    for d in dicts:
        for k, v in d.items():
            text += "%s: %s\n" % (k.capitalize(), v)
        text += '\n'
    return text


def print_dicts(dicts: Sequence[Mapping]) -> str:
    text = ""
    for d in dicts:
        for k, v in d.items():
            text += "%s: %s\n" % (bold(k.capitalize()), v)
        text += '\n'
    return text


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


def plural(num, string, past=False):
    s = '%s %ss' % (num, string) if num != 1 else '%s %s' % (num, string)
    if past:
        s += ' were' if num != 1 else ' was'
    return s

