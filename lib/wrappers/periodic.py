import asyncio
from datetime import datetime, timedelta


def get_next_time(delay):
    now = datetime.now()
    hour = now.hour if delay <= 60 else 0
    start_time = datetime(now.year, now.month, now.day, hour, 0, 0)
    while start_time < now + timedelta(minutes=1):
        start_time += timedelta(minutes=delay)
    td = (start_time - now).total_seconds()
    return td


def _call_cb_at(seconds_from_now, delay, callback, cancel_event, *args):
    loop = asyncio.get_event_loop()
    start_time = loop.time() + seconds_from_now
    return loop.call_at(start_time, _call_cb_now, delay, callback, True, cancel_event, *args)


def _call_cb_later(delay, callback, first, cancel_event, *args):
    return asyncio.get_event_loop().call_later(delay * 60, _call_cb_now, delay, callback, first, cancel_event, *args)


def _call_cb_now(delay, callback, first, cancel_event, *args):
    if not cancel_event.is_set():
        callback(first, *args)
        return _call_cb_later(delay, callback, False, cancel_event, *args)


def call_cb_periodic(delay, callback, *args, fixed_start_time=None, immediate=False):
    cancel_event = asyncio.Event()
    if fixed_start_time:
        start_time = get_next_time(delay)
        _call_cb_at(start_time, delay, callback, cancel_event, *args)
    elif immediate:
        _call_cb_now(delay, callback, cancel_event, *args)
    else:
        _call_cb_later(delay, callback, cancel_event, *args)
    return cancel_event


async def _call_coro_later(delay, coro, *args):
    while True:
        await asyncio.sleep(delay)
        await coro(*args)


async def _call_coro_now(delay, coro, *args):
    await coro(*args)
    await _call_coro_later(delay, coro, *args)


def call_coro_periodic(delay, coro, *args, immediate=False):
    if immediate:
        task = asyncio.create_task(_call_coro_now(delay, coro, *args))
    else:
        task = asyncio.create_task(_call_coro_later(delay, coro, *args))
    return task
