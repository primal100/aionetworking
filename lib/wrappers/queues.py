import asyncio
from lib.compatibility import Protocol


class AsyncioQueueProtocol(Protocol):
    _unfinished_tasks: int
    _finished: asyncio.Event


def multi_task_done(queue: AsyncioQueueProtocol, num: int):
    if queue._unfinished_tasks < num:
        raise ValueError('task_done() called too many times')
    queue._unfinished_tasks -= num
    if queue._unfinished_tasks == 0:
        queue._finished.set()
