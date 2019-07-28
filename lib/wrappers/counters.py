from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Union, DefaultDict

from lib.factories import event_set


@dataclass
class Counter:
    num: int = 0
    is_zero: asyncio.Event = field(default_factory=event_set, init=False)

    def increment(self) -> None:
        self.is_zero.clear()
        self.num += 1

    def decrement(self) -> None:
        if self.num <= 0:
            raise ValueError('counter decremented too many times')
        self.num -= 1
        if self.num == 0:
            self.is_zero.set()

    async def wait_zero(self) -> None:
        await self.is_zero.wait()


class Counters(DefaultDict[Any, Counter]):
    default_factory = Counter

    def __missing__(self, key):
        result = self[key] = self.default_factory()
        return result

    def increment(self, key: Any) -> None:
        self[key].increment()
        pass

    def decrement(self, key: Any) -> None:
        self[key].decrement()

    def get_num(self, key: Any) -> int:
        return self[key].num

    async def wait_zero(self, key: Any, timeout: Union[int, float] = None):
        counter = self[key]
        await asyncio.wait_for(counter.wait_zero(), timeout=timeout)
