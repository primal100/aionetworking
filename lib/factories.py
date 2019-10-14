import asyncio
from collections import defaultdict
from typing import DefaultDict


def event_set() -> asyncio.Event:
    event = asyncio.Event()
    event.set()
    return event


def list_defaultdict() -> DefaultDict:
    return defaultdict(list)


def future_defaultdict() -> DefaultDict:
    return defaultdict(asyncio.Future)


def queue_defaultdict() -> DefaultDict:
    return defaultdict(asyncio.Queue)