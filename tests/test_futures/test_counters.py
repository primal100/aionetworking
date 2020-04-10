import asyncio
import pytest   # noinspection PyPackageRequirements


class TestCounterNum:
    @pytest.mark.asyncio
    async def test_00_counter_wait_immediate_return(self, counter):
        assert counter.num == 0
        await asyncio.wait_for(counter.wait_for(0), timeout=1)

    @pytest.mark.asyncio
    async def test_01_counter_wait_fails(self, counter):
        assert counter.num == 0
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(counter.wait_for(1), timeout=1)

    @pytest.mark.asyncio
    async def test_02_counter_wait_increment(self, counter):
        task = asyncio.create_task(counter.wait_for(2))
        counter.increment()
        assert counter.num == 1
        await asyncio.sleep(0)
        assert not task.done()
        counter.increment()
        await asyncio.sleep(0)
        assert counter.num == 2
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_03_counter_wait_decrement(self, counter):
        counter.increment()
        assert counter.num == 1
        task = asyncio.create_task(counter.wait_for(0))
        await asyncio.sleep(0)
        assert not task.done()
        counter.decrement()
        await asyncio.sleep(0)
        assert counter.num == 0
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    def test_04_raises_below_zero_raises_value_error(self, counter):
        with pytest.raises(ValueError):
            counter.decrement()
        assert counter.num == 0

    def test_05_raises_above_max_raises_value_error(self, counter_with_max):
        for i in range(0, 5):
            counter_with_max.increment()
        assert counter_with_max.num == 5
        with pytest.raises(ValueError):
            counter_with_max.increment()
        assert counter_with_max.num == 5


class TestCounterTotalIncrements:
    @pytest.mark.asyncio
    async def test_00_counter_wait_immediate_return(self, counter):
        assert counter.total_increments == 0
        await asyncio.wait_for(counter.wait_for_total_increments(0), timeout=1)

    @pytest.mark.asyncio
    async def test_01_counter_wait_fails(self, counter):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(counter.wait_for_total_increments(1), timeout=1)
        assert counter.total_increments == 0

    @pytest.mark.asyncio
    async def test_02_counter_wait_increment(self, counter):
        task = asyncio.create_task(counter.wait_for_total_increments(2))
        counter.increment()
        assert counter.total_increments == 1
        await asyncio.sleep(0)
        assert not task.done()
        counter.increment()
        assert counter.total_increments == 2
        await asyncio.sleep(0)
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_03_counter_wait_decrement(self, counter):
        counter.increment()
        assert counter.total_increments == 1
        task = asyncio.create_task(counter.wait_for_total_increments(2))
        await asyncio.sleep(0)
        assert not task.done()
        counter.decrement()
        await asyncio.sleep(0)
        assert counter.total_increments == 1
        assert not task.done()
        counter.increment()
        assert counter.total_increments == 2
        await asyncio.sleep(0)
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    def test_04_raises_above_max_raises_value_error(self, counter_with_max):
        for i in range(0, 5):
            counter_with_max.increment()
        assert counter_with_max.total_increments == 5
        counter_with_max.decrement()
        assert counter_with_max.total_increments == 5
        with pytest.raises(ValueError):
            counter_with_max.increment()


class TestCountersNum:
    @pytest.mark.asyncio
    async def test_00_counters_wait_immediate_return(self, counters):
        assert counters.get_num('abc') == 0
        await asyncio.wait_for(counters.wait_for('abc', 0), timeout=1)

    @pytest.mark.asyncio
    async def test_01_counters_wait_fails(self, counters):
        assert counters.get_num('abc') == 0
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(counters.wait_for('abc', 1), timeout=1)

    @pytest.mark.asyncio
    async def test_02_counters_wait_increment(self, counters):
        task = asyncio.create_task(counters.wait_for('abc', 2))
        counters.increment('abc')
        assert counters.get_num('abc') == 1
        await asyncio.sleep(0)
        assert not task.done()
        counters.increment('abc')
        await asyncio.sleep(0)
        assert counters.get_num('abc') == 2
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_03_counters_wait_decrement(self, counters):
        counters.increment('abc')
        assert counters.get_num('abc') == 1
        task = asyncio.create_task(counters.wait_for('abc', 0))
        await asyncio.sleep(0)
        assert not task.done()
        counters.decrement('abc')
        await asyncio.sleep(0)
        assert counters.get_num('abc') == 0
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_04_multiple(self, counters):
        counters.increment('abc')
        counters.increment('xyz')
        assert counters.get_num('abc') == 1
        assert counters.get_num('xyz') == 1
        task_abc = asyncio.create_task(counters.wait_for('abc', 0))
        task_xyz = asyncio.create_task(counters.wait_for('xyz', 0))
        await asyncio.sleep(0)
        assert not task_abc.done()
        assert not task_xyz.done()
        counters.decrement('abc')
        assert counters.get_num('abc') == 0
        await asyncio.sleep(0)
        try:
            assert task_abc.done()
            assert not task_xyz.done()
            counters.decrement('xyz')
            assert counters.get_num('xyz') == 0
            await asyncio.sleep(0)
            assert task_xyz.done()
        finally:
            await asyncio.wait_for(task_abc, timeout=1)
            await asyncio.wait_for(task_xyz, timeout=1)


class TestCountersTotalIncrements:
    @pytest.mark.asyncio
    async def test_00_counter_wait_immediate_return(self, counters):
        assert counters.total_increments('abc') == 0
        await asyncio.wait_for(counters.wait_for_total_increments('abc', 0), timeout=1)

    @pytest.mark.asyncio
    async def test_01_counter_wait_fails(self, counters):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(counters.wait_for_total_increments('abc', 1), timeout=1)
        assert counters.total_increments('abc') == 0

    @pytest.mark.asyncio
    async def test_02_counter_wait_increment(self, counters):
        task = asyncio.create_task(counters.wait_for_total_increments('abc', 2))
        counters.increment('abc')
        assert counters.total_increments('abc') == 1
        await asyncio.sleep(0)
        assert not task.done()
        counters.increment('abc')
        assert counters.total_increments('abc') == 2
        await asyncio.sleep(0)
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_03_counter_wait_decrement(self, counters):
        counters.increment('abc')
        assert counters.total_increments('abc') == 1
        task = asyncio.create_task(counters.wait_for_total_increments('abc', 2))
        await asyncio.sleep(0)
        assert not task.done()
        counters.decrement('abc')
        await asyncio.sleep(0)
        assert counters.total_increments('abc') == 1
        assert not task.done()
        counters.increment('abc')
        assert counters.total_increments('abc') == 2
        await asyncio.sleep(0)
        try:
            assert task.done()
        finally:
            await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_04_multiple(self, counters):
        counters.increment('abc')
        counters.increment('xyz')
        assert counters.total_increments('abc') == 1
        assert counters.total_increments('xyz') == 1
        task_abc = asyncio.create_task(counters.wait_for_total_increments('abc', 2))
        task_xyz = asyncio.create_task(counters.wait_for_total_increments('xyz', 2))
        await asyncio.sleep(0)
        assert not task_abc.done()
        assert not task_xyz.done()
        counters.decrement('abc')
        assert counters.total_increments('abc') == 1
        assert counters.total_increments('xyz') == 1
        await asyncio.sleep(0)
        try:
            assert not task_abc.done()
            assert not task_xyz.done()
            counters.increment('xyz')
            assert counters.total_increments('xyz') == 2
            await asyncio.sleep(0)
            assert task_xyz.done()
            assert not task_abc.done()
        finally:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(task_abc, timeout=1)
            await asyncio.wait_for(task_xyz, timeout=1)
