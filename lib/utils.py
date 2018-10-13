import datetime
import sys
import os
import csv
import struct
import re
import asyncio


def data_directory(APPNAME):
    if sys.platform == 'win32':
        home = os.path.join(os.environ['APPDATA'], APPNAME)
    else:
        home = os.path.expanduser(os.path.join("~", "." + APPNAME))
    return home

def timestamp_to_utc_string(timestamp):
    return ''.join(timestamp)

def timestamp_to_string(timestamp):
    return ''.join(timestamp)


def asn_timestamp_to_datetime(timestamp):
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


def datetime_to_human_readable(dt, strf='%Y-%m-%d %H:%M:%S.%f'):
    if not dt.microsecond:
        strf = strf.replace('.%f', '')
        return dt.strftime(strf)
    return dt.strftime(strf)[:-5]


def datetime_to_timestamp(dt):
    pass


def datetime_now_pprint(dt):
    return datetime.datetime.now().strftime("")


def current_date():
    return datetime.datetime.now().strftime("%Y%m%d")


def get_value_by_path(d, path, default=None):
    pass


def append_to_csv(filepath, lines):
    with open(filepath, 'a+') as f:
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        writer.writerows(lines)


def adapt_asn_domain(domain):
    return '.'.join([str(x) for x in domain])


def write_to_files(base_path, write_mode, file_writes):
    """
    Takes a dictionary containing filepaths (keys) and data to write to each one (values)
    """
    os.makedirs(base_path, exist_ok=True)
    for file_name in file_writes.keys():
        file_path = os.path.join(base_path, file_name)
        with open(file_path, write_mode) as f:
            f.write(file_writes[file_name])


def unique_filename(basefilepath, filename, extension):
    filename_no_extension = filename.split('.%s' % extension)[0]
    filepath = basefilepath + "." + extension
    i = 1
    while os.path.exists(filepath):
        filepath = "%s_%s.%s" % (filename_no_extension, i, extension)
        i += 1
    return filepath


def write_to_unique_filename(basepath, basefilename, extension, content, mode='w'):
    if not os.path.exists(basepath):
        os.makedirs(basepath)
    basefilepath = os.path.join(basepath, basefilename)
    filepath = unique_filename(basefilepath, basefilename, extension)
    with open(filepath, mode) as f:
        f.write(content)

def pack_binary(content):
    return struct.pack("I", len(content)) + content


def camel_case_to_title(string):
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


def bold(text):
    return Color.BOLD + text + Color.END


def underline(text):
    return Color.UNDERLINE + text + Color.END


def store_dicts(dicts):
    text = ""
    for d in dicts:
        for k, v in d.items():
            text += "%s: %s\n" % (k.capitalize(), v)
        text += '\n'
    return text


def print_dicts(dicts):
    text = ""
    for d in dicts:
        for k, v in d.items():
            text += "%s: %s\n" % (bold(k.capitalize()), v)
        text += '\n'
    return text
