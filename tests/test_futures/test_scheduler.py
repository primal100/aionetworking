import pytest
import asyncio


class TestTaskScheduler:

    @pytest.mark.asyncio
    async def test_00_task_lifecycle(self, task_scheduler):
        await asyncio.wait_for(task_scheduler.close(), timeout=0.1)
        task = task_scheduler.create_task(asyncio.sleep(0.2), name="Test")
        await asyncio.sleep(0)
        assert not task.done()
        await asyncio.sleep(0.3)
        await asyncio.wait_for(task, timeout=1)
        task_scheduler.task_done(task)

    @pytest.mark.asyncio
    async def test_01_task_done_value_error(self, task_scheduler):
        with pytest.raises(ValueError):
            task_scheduler.task_done(asyncio.Future())

    @pytest.mark.asyncio
    async def test_02_future_lifecycle(self, task_scheduler):
        await asyncio.wait_for(task_scheduler.close(), timeout=1)
        fut = task_scheduler.create_future(1)
        task = asyncio.create_task(task_scheduler.close())
        await asyncio.sleep(0)
        assert not task.done()
        task_scheduler.set_result(1, "abc")
        await fut
        assert fut.result() == 'abc'
        task_scheduler.future_done(1)

    @pytest.mark.asyncio
    async def test_03_future_set_exception(self, task_scheduler):
        fut = task_scheduler.create_future(2)
        task_scheduler.set_exception(2, ValueError())
        with pytest.raises(ValueError):
            await fut
        task_scheduler.future_done(2)

    @pytest.mark.asyncio
    async def test_04_future_run_wait(self, task_scheduler):
        def set_result(res: str):
            task_scheduler.set_result(3, res)
        result = await task_scheduler.run_wait_fut(3, set_result, 'abc')
        assert result == 'abc'

    @pytest.mark.asyncio
    async def test_05_future_run_wait_exception(self, task_scheduler):
        def set_result(res: str):
            task_scheduler.set_exception(3, ValueError())
        with pytest.raises(ValueError):
            await task_scheduler.run_wait_fut(3, set_result, 'abc')

    @pytest.mark.parametrize('delay,start_interval', [
            pytest.param(3600, 3540.0, id='hourly'),
            pytest.param(7200, 3540.0, id='2-hourly'),
            pytest.param(10800, 7140.0, id='3-hourly'),
    ])
    @pytest.mark.asyncio
    async def test_06_get_next_time(self, task_scheduler, delay, start_interval, fixed_timestamp):
        interval = task_scheduler.get_next_time(delay)
        assert interval == start_interval

    @pytest.mark.parametrize('fixed_start_time,immediate,delay,start_interval', [
        pytest.param(False, True, 3600, 0, id='hourly'),
        pytest.param(True, False, 3600, 3540.0, id='2-hourly'),
        pytest.param(True, True, 7200, 3540.0, id='3-hourly'),
    ])
    @pytest.mark.asyncio
    async def test_07_get_start_interval(self, task_scheduler, fixed_start_time, immediate, delay, start_interval,
                                         fixed_timestamp):
        interval = task_scheduler.get_start_interval(fixed_start_time, immediate, delay)
        assert interval == start_interval

    @pytest.mark.parametrize('immediate,num,coro_or_cb', [(True, 3, 'coro'), (False, 2, 'cb')])
    @pytest.mark.asyncio
    async def test_08_periodic_coro_lifecycle(self, task_scheduler, immediate, num, coro_or_cb):
        queue = asyncio.Queue()
        if coro_or_cb == 'coro':
            task_scheduler.call_coro_periodic(0.1, queue.put, 'abc', immediate=immediate)
        else:
            task_scheduler.call_cb_periodic(0.1, queue.put_nowait, 'abc', immediate=immediate)
        await asyncio.sleep(0.25)
        await task_scheduler.close()
        await asyncio.sleep(0.15)
        assert queue.qsize() == num
