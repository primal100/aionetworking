import pytest
import asyncio
from aionetworking.compatibility import supports_task_name
from aionetworking import Counters, Counter, TaskScheduler


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
        task = asyncio.create_task(coro(), name="Task-99")
    else:
        task = asyncio.create_task(coro())
    yield task
    await task
