import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import sys
from typing import Any, Callable, Awaitable, List, Union, Dict, Optional, Type

from aionetworking.compatibility import set_task_name, create_task
from .counters import Counter


@dataclass
class TaskScheduler:
    _counter: Counter = field(default_factory=Counter, init=False)
    _futures: Dict[Any, asyncio.Future] = field(default_factory=dict, init=False)
    _periodic_tasks: List[asyncio.Future] = field(default_factory=list, init=False)
    _current_tasks: List[asyncio.Future] = field(default_factory=list, init=False)

    def task_done(self, future: asyncio.Future) -> None:
        self._counter.decrement()
        if future in self._current_tasks:
            self._current_tasks.remove(future)

    def create_task(self, coro: Awaitable, name: str = None, include_hierarchy: bool = True,
                    separator: str = ':', continuous: bool = False) -> asyncio.Future:
        self._counter.increment()
        task = create_task(coro)
        set_task_name(task, name, include_hierarchy=include_hierarchy, separator=separator)
        if not continuous:
            self._current_tasks.append(task)
        return task

    def task_with_callback(self, coro: Awaitable, callback: Callable = None, name: str = None,
                           include_hierarchy: bool = True, separator: str = ':', continuous: bool = False) -> asyncio.Future:
        task = self.create_task(coro, name=name, include_hierarchy=include_hierarchy, separator=separator, continuous=continuous)
        callback = callback or self.task_done
        task.add_done_callback(callback)
        return task

    def create_future(self, name: Any) -> asyncio.Future:
        self._counter.increment()
        fut = asyncio.Future()
        self._futures[name] = fut
        return fut

    def _call_cb_with_task_done(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        finally:
            self._counter.decrement()

    def call_soon(self, callback: Callable, *args):
        self._counter.increment()
        asyncio.get_event_loop().call_soon(self._call_cb_with_task_done, callback, *args)

    def future_done(self, name: Any) -> None:
        fut = self._futures.pop(name)
        self.task_done(fut)

    async def run_wait_fut(self, name: Any, callback: Callable, *args, **kwargs) -> Any:
        fut = self.create_future(name)
        try:
            callback(*args, **kwargs)
            await fut
            return fut.result()
        finally:
            self.future_done(name)

    def set_result(self, name: Any, result: Any) -> None:
        self._futures[name].set_result(result)

    def set_exception(self, name: Any, exception: BaseException) -> None:
        self._futures[name].set_exception(exception)

    def cancel_all_futures(self, exc_class: Optional[Type[BaseException]]):
        for name, fut in self._futures.items():
            if not fut.cancelled() and not fut.done():
                fut.set_exception(exc_class())

    async def join(self) -> None:
        await self._counter.wait_for(0)

    async def wait_current_tasks(self) -> None:
        if self._current_tasks:
            current_tasks = self._current_tasks.copy()
            await asyncio.wait(current_tasks)

    async def close(self) -> None:
        self.close_nowait()
        await self.join()
        await asyncio.gather(*self._periodic_tasks, return_exceptions=True)
        self._periodic_tasks.clear()

    def close_nowait(self):
        for task in self._periodic_tasks:
            task.cancel()

    @staticmethod
    def get_next_time(delay: Union[int, float]) -> float:
        now = datetime.now()
        hour = now.hour if delay <= 60 else 0
        start_time = datetime(now.year, now.month, now.day, hour, 0, 0)
        while start_time < now + timedelta(minutes=1):
            start_time += timedelta(seconds=delay)
        td = (start_time - now).total_seconds()
        return td

    def get_start_interval(self, fixed_start_time: bool, immediate: bool, delay: Union[int, float]):
        if fixed_start_time:
            return self.get_next_time(delay)
        elif immediate:
            return 0
        else:
            return delay

    @staticmethod
    async def _call_coro_periodic(interval: Union[int, float], async_callback: Callable, *args,
                                  start_time_interval: Union[int, float] = 0, **kwargs):
        # Asyncio.sleep wrong time on MacOS
        await asyncio.sleep(start_time_interval)
        while True:
            coro = async_callback(*args, **kwargs)
            await coro
            await asyncio.sleep(interval)

    def call_coro_periodic(self, interval: Union[int, float], async_callback: Callable, *args,
                           fixed_start_time: bool = False, immediate: bool = False, task_name: str = None,
                           **kwargs) -> None:
        start_time_interval = self.get_start_interval(fixed_start_time, immediate, interval)
        task = create_task(
            self._call_coro_periodic(interval, async_callback, start_time_interval=start_time_interval, *args, **kwargs))
        set_task_name(task, task_name)
        self._periodic_tasks.append(task)

    @staticmethod
    async def _call_cb(callback: Callable, *args, **kwargs):
        return callback(*args, **kwargs)

    def call_cb_periodic(self, interval: Union[int, float], cb: Callable, *args, task_name: str = None, **kwargs):
        self.call_coro_periodic(interval, self._call_cb, cb, *args, task_name=task_name, **kwargs)
