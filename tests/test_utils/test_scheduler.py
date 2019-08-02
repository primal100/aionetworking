import pytest
import asyncio
from datetime import datetime


class TestTaskScheduler:

    @pytest.mark.asyncio
    async def test_00_task_lifecycle(self, task_scheduler):
        await task_scheduler.close(timeout=1)
        task = task_scheduler.create_task(asyncio.sleep(0.2))
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(task_scheduler.join(), timeout=0.1)
        await task
        await asyncio.wait_for(task_scheduler.join(), timeout=1)
        done, pending = await task_scheduler.close(timeout=1)
        assert len(done) == 1
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_01_promise_success(self, task_scheduler, future, wait_get_double_coro, success, fail):
        task_scheduler.create_promise(wait_get_double_coro(0.3, 3), success, fail, fut=future)
        result = await future
        assert result == 6
        await asyncio.wait_for(task_scheduler.join(), timeout=1)

    @pytest.mark.asyncio
    async def test_02_promise_exception(self, task_scheduler, future, wait_get_double_coro, success, fail):
        task_scheduler.create_promise(wait_get_double_coro(0.3, 5), success, fail, fut=future)
        with pytest.raises(ValueError):
            await future
        await asyncio.wait_for(task_scheduler.join(), timeout=1)

    @pytest.mark.asyncio
    async def test_03_task_done_value_error(self, task_scheduler):
        with pytest.raises(ValueError):
            task_scheduler.task_done(asyncio.Future())

    @pytest.mark.asyncio
    async def test_04_future_lifecycle(self, task_scheduler):
        await task_scheduler.close(timeout=1)
        fut = task_scheduler.create_future(1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(task_scheduler.join(), timeout=0.1)
        done, pending = await task_scheduler.close(timeout=0.3)
        assert len(done) == 0
        assert len(pending) == 1
        task_scheduler.set_result(1, "abc")
        await fut
        assert fut.result() == 'abc'
        task_scheduler.future_done(1)
        await asyncio.wait_for(task_scheduler.join(), timeout=1)
        done, pending = await task_scheduler.close(timeout=1)
        assert len(done) == 1
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_05_future_set_exception(self, task_scheduler):
        fut = task_scheduler.create_future(2)
        task_scheduler.set_exception(2, ValueError())
        with pytest.raises(ValueError):
            await fut
        task_scheduler.future_done(2)
        await asyncio.wait_for(task_scheduler.join(), timeout=1)

    @pytest.mark.asyncio
    async def test_06_future_run_wait(self, task_scheduler):
        def set_result(res: str):
            task_scheduler.set_result(3, res)
        fut = await task_scheduler.run_wait_fut(3, set_result, 'abc')
        assert fut.result() == 'abc'
        await task_scheduler.close(timeout=1)

    @pytest.mark.asyncio
    async def test_07_future_run_wait_exception(self, task_scheduler):
        def set_result(res: str):
            task_scheduler.set_exception(3, ValueError())
        with pytest.raises(ValueError):
            await task_scheduler.run_wait_fut(3, set_result, 'abc')
        await task_scheduler.close(timeout=1)

    @pytest.mark.parametrize('delay,start_interval', [(
            3600, 1800.0),
            (7200, 5400.0)])
    @pytest.mark.asyncio
    async def test_08_get_next_time(self, task_scheduler, delay, start_interval):
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
    async def test_09_get_start_interval(self, task_scheduler, fixed_start_time, immediate, delay, start_interval):
        current_time = datetime(2019, 1, 1, 6, 30)
        interval = task_scheduler.get_start_interval(fixed_start_time, immediate, delay, current_time=current_time)
        assert interval == start_interval

    @pytest.mark.parametrize('immediate,num', [(True, 3), (False, 2)])
    @pytest.mark.asyncio
    async def test_10_periodic_coro_lifecycle(self, task_scheduler, immediate, num):
        queue = asyncio.Queue()
        task_scheduler.call_coro_periodic(0.1, queue.put, 'abc', immediate=immediate)
        await asyncio.sleep(0.25)
        await task_scheduler.close()
        await asyncio.sleep(0.15)
        assert queue.qsize() == num

    @pytest.mark.asyncio
    @pytest.mark.parametrize('immediate,num', [(True, 3), (False, 2)])
    async def test_11_periodic_cb_lifecycle(self, task_scheduler, immediate, num):
        queue = asyncio.Queue()
        task_scheduler.call_cb_periodic(0.1, queue.put_nowait, 'abc', immediate=immediate)
        await asyncio.sleep(0.25)
        await task_scheduler.close()
        await asyncio.sleep(0.15)
        assert queue.qsize() == num