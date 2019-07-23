import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, List, Union, MutableMapping


@dataclass
class TaskScheduler:
    _unfinished_tasks = 0
    _finished: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _futures: MutableMapping[Any, asyncio.Future] = field(default_factory=dict, init=False)
    _periodic_tasks: List[asyncio.Future] = field(default_factory=list, init=False)

    def __post_init__(self):
        self._finished.set()

    def task_done(self, future: asyncio.Future) -> None:
        if self._unfinished_tasks <= 0:
            raise ValueError('task_done() called too many times')
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    def _increment_unfinished(self):
        self._finished.clear()
        self._unfinished_tasks += 1

    def create_task(self, coro: Awaitable, callback: Callable = None) -> asyncio.Future:
        self._increment_unfinished()
        task = asyncio.ensure_future(coro)
        callback = callback or self.task_done
        task.add_done_callback(callback)
        return task

    def create_future(self, id_: Any) -> asyncio.Future:
        self._increment_unfinished()
        fut = asyncio.Future()
        self._futures[id_] = fut
        return fut

    def future_done(self, id_: Any) -> None:
        fut = self._futures.pop(id_)
        self.task_done(fut)

    def set_result(self, id_: Any, result: Any) -> None:
        self._futures[id_].set_result(result)

    def set_exception(self, id_: Any, exception: BaseException) -> None:
        self._futures[id_].set_exception(exception)

    async def join(self) -> None:
        if self._unfinished_tasks > 0:
            await self._finished.wait()

    async def close(self, timeout: Union[int, float] = None):
        for task in self._periodic_tasks:
            task.cancel()
        futs = [self.join()] + self._periodic_tasks
        return await asyncio.wait(futs, timeout=timeout)

    @staticmethod
    def get_next_time(delay: Union[int, float], current_time: datetime = None) -> float:
        now = current_time or datetime.now()
        hour = now.hour if delay <= 60 else 0
        start_time = datetime(now.year, now.month, now.day, hour, 0, 0)
        while start_time < now + timedelta(minutes=1):
            start_time += timedelta(seconds=delay)
        td = (start_time - now).total_seconds()
        return td

    def get_start_interval(self, fixed_start_time: bool, immediate: bool, delay: Union[int, float], current_time: datetime = None):
        if fixed_start_time:
            return self.get_next_time(delay, current_time=current_time)
        elif immediate:
            return 0
        else:
            return delay

    @staticmethod
    async def _call_coro_periodic(delay: Union[int, float], async_callback: Callable,
                             *args, start_time_interval: Union[int, float] = 0, **kwargs):
        await asyncio.sleep(start_time_interval)
        while True:
            coro = async_callback(*args, **kwargs)
            asyncio.create_task(coro)
            await asyncio.sleep(delay)

    def call_coro_periodic(self, delay: Union[int, float], async_callback: Callable, *args,
                           fixed_start_time: bool = False, immediate: bool = False, **kwargs) -> asyncio.Task:
        start_time_interval = self.get_start_interval(fixed_start_time, immediate, delay)
        task = asyncio.create_task(
            self._call_coro_periodic(delay, async_callback, start_time_interval=start_time_interval, *args, **kwargs))
        self._periodic_tasks.append(task)
        return task

    @staticmethod
    async def _call_cb(callback: Callable, *args, **kwargs):
        return callback(*args, **kwargs)

    def call_cb_periodic(self, delay: Union[int, float], cb: Callable, *args, **kwargs):
        self.call_coro_periodic(delay, self._call_cb, cb, *args, **kwargs)
