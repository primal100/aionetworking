
import asyncio
from collections import defaultdict
from typing import DefaultDict


def future_defaultdict() -> DefaultDict:
    return defaultdict(asyncio.Future)


def queue_defaultdict() -> DefaultDict:
    return defaultdict(asyncio.Queue)