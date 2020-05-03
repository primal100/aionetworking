import pytest
import asyncio
from aionetworking.compatibility import supports_task_name, create_task
from aionetworking import Counters, Counter, TaskScheduler

from typing import Callable, Union


@pytest.fixture
async def future():
    yield asyncio.Future()


@pytest.fixture
def wait_get_double_coro() -> Callable:
    async def wait_get_double(delay: Union[int, float], num: int):
        await asyncio.sleep(delay)
        if num > 4:
            raise ValueError()
        return num * 2
    return wait_get_double


@pytest.fixture
async def counter() -> Counter:
    yield Counter()


@pytest.fixture
async def counter_with_max() -> Counter:
    yield Counter(max=5, max_increments=5)


@pytest.fixture
async def counters() -> Counters:
    yield Counters()


@pytest.fixture
async def task_scheduler() -> TaskScheduler:
    scheduler = TaskScheduler()
    yield scheduler
    await asyncio.wait_for(scheduler.close(), timeout=1)


@pytest.fixture
async def task() -> asyncio.Task:
    async def coro(): ...
    if supports_task_name():
        task = create_task(coro(), name="Task-99")
    else:
        task = create_task(coro())
    yield task
    await task
