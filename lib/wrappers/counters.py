import asyncio
from dataclasses import dataclass, field
from typing import Dict, Union


@dataclass
class Counter:
    num: int = 0
    max: int = -1
    is_zero: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    is_full: asyncio.Event = field(default_factory=asyncio.Event, init=False)

    def increment(self):
        self.is_zero.clear()
        if not self.num == self.max:
            self.num += 1
            if self.num == self.max:
                self.is_full.set()

    def decrement(self):
        if self.num <= 0:
            raise ValueError('counter decremented too many times')
        self.num -= 1
        if self.num == 0:
            self.is_zero.set()
        self.is_full.clear()

    async def wait_zero(self, timeout: Union[int, float] = None) -> None:
        if self.num:
            await asyncio.wait_for(self.is_zero.wait(), timeout=timeout)

    async def wait_full(self, timeout: Union[int, float] = None) -> None:
        if not self.num == self.max:
            await asyncio.wait_for(self.is_full.wait(), timeout=timeout)


class Counters(Dict[int, Counter]):
    def increment(self, key: int):
        if key not in self:
            self[key] = Counter()
        self[key].increment()

    def decrement(self, key: int):
        self[key].decrement()

    def get_num(self, key: int):
        return self[key].num

    async def wait_full(self, key: int, timeout: Union[int, float] = None):
        await self[key].wait_full(timeout=timeout)

    async def wait_zero(self, key: int, timeout: Union[int, float] = None):
        await self[key].wait_zero(timeout=timeout)
