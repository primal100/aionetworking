import pytest
import asyncio
from datetime import datetime


class TestTaskScheduler:

    @pytest.mark.asyncio
    async def test_00_task_lifecycle(self, task_scheduler):
        assert task_scheduler._finished.is_set()
        assert task_scheduler._unfinished_tasks == 0
        task = task_scheduler.create_task(asyncio.sleep(0.5))
        assert not task_scheduler._finished.is_set()
        assert task_scheduler._unfinished_tasks == 1
        await task
        assert task_scheduler._unfinished_tasks == 0
        assert task_scheduler._finished.is_set()
        await task_scheduler.join()
        await task_scheduler.close()

    @pytest.mark.asyncio
    async def test_01_task_done_value_error(self, task_scheduler):
        with pytest.raises(ValueError):
            task_scheduler.task_done(asyncio.Future())

    @pytest.mark.asyncio
    async def test_02_future_lifecycle(self, task_scheduler):
        assert task_scheduler._finished.is_set()
        assert task_scheduler._unfinished_tasks == 0
        fut = task_scheduler.create_future(1)
        assert not task_scheduler._finished.is_set()
        assert task_scheduler._unfinished_tasks == 1
        done, pending = await task_scheduler.close(timeout=0.3)
        assert len(done) == 0
        assert len(pending) == 1
        task_scheduler.set_result(1, "abc")
        result = await fut
        assert result == 'abc'
        task_scheduler.future_done(1)
        assert task_scheduler._unfinished_tasks == 0
        assert task_scheduler._finished.is_set()
        await task_scheduler.join()
        await task_scheduler.close()

    @pytest.mark.parametrize('delay,start_interval', [(
            3600, 1800.0),
            (7200, 5400.0)])
    @pytest.mark.asyncio
    async def test_03_get_next_time(self, task_scheduler, delay, start_interval):
        current_time = datetime(2019, 1, 1, 6, 30)
        interval = task_scheduler.get_next_time(delay, current_time=current_time)
        assert interval == start_interval

    @pytest.mark.parametrize('fixed_start_time,immediate,delay,start_interval', [
        (False, True, 3600, 0),
        (True, False, 3600, 1800.0),
        (True, True, 7200, 5400.0),
        (False, False, 7200, 7200.0),
    ])
    @pytest.mark.asyncio
    async def test_04_get_start_interval(self, task_scheduler, fixed_start_time, immediate, delay, start_interval):
        current_time = datetime(2019, 1, 1, 6, 30)
        interval = task_scheduler.get_start_interval(fixed_start_time, immediate, delay, current_time=current_time)
        assert interval == start_interval

    @pytest.mark.parametrize('immediate,num', [(True, 3), (False, 2)])
    @pytest.mark.asyncio
    async def test_05_periodic_coro_lifecycle(self, task_scheduler, immediate, num):
        queue = asyncio.Queue()
        task_scheduler.call_coro_periodic(0.1, queue.put, 'abc', immediate=immediate)
        await asyncio.sleep(0.25)
        await task_scheduler.close()
        await asyncio.sleep(0.15)
        assert queue.qsize() == num

    @pytest.mark.asyncio
    @pytest.mark.parametrize('immediate,num', [(True, 3), (False, 2)])
    async def test_06_periodic_cb_lifecycle(self, task_scheduler, immediate, num):
        queue = asyncio.Queue()
        task_scheduler.call_cb_periodic(0.1, queue.put_nowait, 'abc', immediate=immediate)
        await asyncio.sleep(0.25)
        await task_scheduler.close()
        await asyncio.sleep(0.15)
        assert queue.qsize() == num
