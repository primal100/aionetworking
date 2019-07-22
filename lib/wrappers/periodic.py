import asyncio
from datetime import datetime, timedelta
from typing import Callable, Union


def get_next_time(delay: Union[int, float]) -> float:
    now = datetime.now()
    hour = now.hour if delay <= 60 else 0
    start_time = datetime(now.year, now.month, now.day, hour, 0, 0)
    while start_time < now + timedelta(minutes=1):
        start_time += timedelta(minutes=delay)
    td = (start_time - now).total_seconds()
    return td


def _call_cb_at(seconds_from_now: float, delay: Union[int, float], callback: Callable, cancel_event: asyncio.Event,
                *args) -> asyncio.Handle:
    loop = asyncio.get_event_loop()
    start_time = loop.time() + seconds_from_now
    return loop.call_at(start_time, _call_cb_now, delay, callback, True, cancel_event, *args)


def _call_cb_later(delay: Union[int, float], callback: Callable, first: bool, cancel_event: asyncio.Event, *args) -> asyncio.Handle:
    return asyncio.get_event_loop().call_later(delay * 60, _call_cb_now, delay, callback, first, cancel_event, *args)


def _call_cb_now(delay: Union[int, float], callback: Callable, first: bool, cancel_event: asyncio.Event, *args):
    if not cancel_event.is_set():
        callback(first, *args)
        _call_cb_later(delay, callback, False, cancel_event, *args)


def call_cb_periodic(delay: Union[int, float], callback: Callable, *args, fixed_start_time: bool = None,
                     immediate: bool = False) -> asyncio.Event:
    cancel_event = asyncio.Event()
    if fixed_start_time:
        start_time = get_next_time(delay)
        _call_cb_at(start_time, delay, callback, cancel_event, *args)
    elif immediate:
        _call_cb_now(delay, callback, True, cancel_event, *args)
    else:
        _call_cb_later(delay, callback, True, cancel_event, *args)
    return cancel_event


async def _call_coro_now(delay: Union[int, float], async_callback: Callable, *args, immediate: bool = False, **kwargs):
    if not immediate:
        await asyncio.sleep(delay)
    while True:
        coro = async_callback(*args, **kwargs)
        await coro
        await asyncio.sleep(delay)


def call_coro_periodic(delay: Union[int, float], async_callback: Callable, *args,
                       immediate: bool = False) -> asyncio.Task:
    task = asyncio.create_task(_call_coro_now(delay, async_callback, immediate=immediate, *args))
    return task
