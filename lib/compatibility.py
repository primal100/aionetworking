import asyncio
import sys


py38 = sys.version_info >= (3, 8)


if py38:
    from typing import Protocol
else:
    from typing_extensions import Protocol


if py38:
    def set_task_name(task: asyncio.Future, name):
        if name is not None and isinstance(task, asyncio.Task):
            task.set_name(name)

    def get_task_name(task: asyncio.Task) -> str:
        return task.get_name()
else:
    def set_task_name(task, name): ...

    def get_task_name(task: asyncio.Future) -> None: ...


def datagram_supported(loop: asyncio.AbstractEventLoop = None):
    loop = loop or asyncio.get_event_loop()
    return py38 or not isinstance(loop, asyncio.ProactorEventLoop)
