
import asyncio
from dataclasses import dataclass, field

from aionetworking.factories import future_defaultdict
from typing import Dict, Sequence, Any, List


class StatusException(BaseException): ...


@dataclass
class ValueWaiter:
    values: Sequence[Any] = ()
    _waiters: Dict[Any, asyncio.Future] = field(default_factory=future_defaultdict, init=False)
    _val: str = field(default='', init=False)
    _historical_values: List[Any] = field(default_factory=list, init=False)

    def has_had_value(self, value: str):
        return value in self._historical_values

    async def wait_has_had_value(self, value: str):
        if self.has_had_value(value):
            return
        if value not in self.values:
            raise StatusException(f'{value} is not a valid value')
        await self._waiters[value]

    def is_value(self, value: str):
        return self._val == value

    def is_one_of(self, values: Sequence[Any]):
        return any(v == self._val for v in values)

    async def wait_value(self, value: str):
        if self._val == value:
            return
        if value not in self.values:
            raise StatusException(f'{value} is not a valid value')
        await self._waiters[value]

    def _check_waiters(self):
        if self._val in self._waiters:
            if not self._waiters[self._val].done():
                self._waiters[self._val].set_result(True)
            self._waiters.pop(self._val)

    def set_value(self, value: str):
        if value not in self.values:
            raise StatusException(f'{value} is not a valid value')
        self._val = value
        if value not in self._historical_values:
            self._historical_values.append(value)
        self._check_waiters()

    def set_exception(self, value: str, exc: BaseException):
        if value in self._waiters:
            self._waiters[value].set_exception(exc)
            self._waiters.pop(value)


@dataclass
class StatusWaiter(ValueWaiter):
    values: Sequence[Any] = ('stopped', 'starting', 'started', 'stopping')
    _val: str = field(default='stopped', init=False)

    async def wait_started(self):
        return await self.wait_value('started')

    async def wait_starting(self):
        return await self.wait_value('starting')

    async def wait_stopped(self):
        return await self.wait_value('stopped')

    async def wait_stopping(self):
        return await self.wait_value('stopping')

    async def wait_starting_or_started(self):
        return await asyncio.wait([self.wait_started(), self.wait_starting()], return_when=asyncio.FIRST_COMPLETED)

    async def wait_stopping_or_stopped(self):
        return await asyncio.wait([self.wait_stopped(), self.wait_stopping()], return_when=asyncio.FIRST_COMPLETED)

    async def wait_has_started(self):
        return await self.wait_has_had_value('started')

    def has_started(self):
        return self.has_had_value('started')

    def is_started(self):
        return self.is_value('started')

    def is_stopped(self):
        return self.is_value('stopped')

    def is_starting_or_started(self):
        return self.is_one_of(['started', 'starting'])

    def is_stopping_or_stopped(self):
        return self.is_one_of(['stopped', 'stopping'])

    def set_started(self):
        self.set_value('started')

    def set_stopped(self):
        self.set_value('stopped')

    def set_stopping(self):
        self.set_value('stopping')

    def set_starting(self):
        self.set_value('starting')
