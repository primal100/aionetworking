import asyncio
from typing import Any


class NextResultFuture:
    def __init__(self):
        self._current_future = asyncio.Future()
        self._next_future = None

    @property
    async def fut(self):
        if self._next_future:
            return self._next_future
        return self._current_future

    def pause(self):
        self._next_future = asyncio.Future()

    def _reset(self):
        self._current_future = self._next_future
        self._next_future = None

    def set_result(self, result: Any):
        self._current_future.set_result(result)
        self._reset()

    def set_exception(self, exc: BaseException):
        self._current_future.set_result(exc)
        self._reset()