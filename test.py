import os
from pathlib import Path
import threading
from threading import Event
import asyncio
import aiofiles
from aiofile import AIOFile
import shutil

num_bytes = 100
num_files = 100
path = Path('data')

import time

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % \
                    (method.__name__, (te - ts) * 1000))
        return result
    return timed

def setup():
    try:
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(exist_ok=True)
    except OSError:
        pass

def write(filename, data):
    for filename, data in file_writes:
        with Path(path, filename).open('wb') as f:
             f.write(data)


def write_with_event(filename, data, event):
    write(filename, data)
    event.set()


@timeit
def traditional(file_writes):
    for filename, data in file_writes:
        write(filename, data)


@timeit
def threaded(file_writes):
    events = []
    for filename, data in file_writes:
        event = Event()
        t = threading.Thread(target=write_with_event, args=(filename, data, event))
        t.start()
        events.append(event)
    for event in events:
        event.wait()


async def write_with_aiofiles(filename, data, event):
      async with aiofiles.open(Path(path, filename), mode='wb') as f:
              await f.write(data)
      event.set()


async def aiofiles_test(file_writes):
    events = []
    for filename, data in file_writes:
        event = asyncio.Event()
        asyncio.create_task(write_with_aiofiles(filename, data, event))
        events.append(event)
    for event in events:
        await event.wait()


@timeit
def aiofiles_event_loop(file_writes):
    asyncio.run(aiofiles_test(file_writes))


async def write_with_aiofile(filename, data, event):
      async with AIOFile(Path(path, filename), mode='wb') as f:
            await f.write(data)
      event.set()


async def aiofile_test(file_writes):
      events = []
      for filename, data in file_writes:
          event = asyncio.Event()
          asyncio.create_task(write_with_aiofile(filename, data, event))
          events.append(event)
      for event in events:
          await event.wait()


@timeit
def aiofile_event_loop(file_writes):
    asyncio.run(aiofile_test(file_writes))


data = os.urandom(num_bytes)
file_writes = [('file_%s' % i, data) for i in range(0, num_files)]

#setup()
#traditional(file_writes)
#setup()
#threaded(file_writes)
setup()
aiofiles_event_loop(file_writes)
setup()
aiofile_event_loop(file_writes)