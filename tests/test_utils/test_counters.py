import asyncio
import pytest


class TestCounters:
    @pytest.mark.asyncio
    async def test_00_counter_ok(self, counter):
        assert counter.is_zero.is_set() is True
        await asyncio.wait_for(counter.wait_zero(), timeout=1)
        counter.increment()
        assert counter.num == 1
        assert counter.is_zero.is_set() is False
        counter.decrement()
        assert counter.num == 0
        assert counter.is_zero.is_set() is True
        await asyncio.wait_for(counter.wait_zero(), timeout=1)

    def test_01_raises_value_error(self, counter):
        with pytest.raises(ValueError):
            counter.decrement()

    @pytest.mark.asyncio
    async def test_02_raises_timeout_error(self, counter):
        counter.increment()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(counter.wait_zero(), timeout=0.1)


class TestCounter:
    @pytest.mark.asyncio
    async def test_00_counters_ok(self, counters):
        assert counters.get_num('abc') == 0
        counters.increment('abc')
        assert counters.get_num('abc') == 1
        counters.increment('xyz')
        counters.decrement('abc')
        assert counters.get_num('abc') == 0
        assert counters.get_num('xyz') == 1
        await counters.wait_zero('abc', timeout=0.1)
        counters.decrement('xyz')
        assert counters.get_num('xyz') == 0
        await counters.wait_zero('xyz', timeout=0.1)

    def test_01_raises_value_error(self, counters):
        counters.increment('abc')
        counters.decrement('abc')
        with pytest.raises(ValueError):
            counters.decrement('abc')

    @pytest.mark.asyncio
    async def test_02_raises_timeout_error(self, counters):
        counters.increment('abc')
        counters.increment('xyz')
        counters.decrement('abc')
        await counters.wait_zero('abc', timeout=0.1)
        with pytest.raises(asyncio.TimeoutError):
            await counters.wait_zero('xyz', timeout=0.1)
