import asyncio
import sys


py38 = sys.version_info >= (3, 8)


if py38:
    from typing import Protocol
else:
    from typing_extensions import Protocol


def set_task_name(task: asyncio.Future, name: str, include_hierarchy: bool = True, separator: str = ':'):
    if hasattr(task, "set_name"):
        name = name if name else get_task_name(task)
        if include_hierarchy:
            prefix = get_current_task_name()
            name = name if prefix == 'No Running Loop' else f"{prefix}{separator}{name}"
        task.set_name(name)


def get_task_name(task: asyncio.Future) -> str:
    if hasattr(task, "get_name"):
        return task.get_name()
    return str(id(task))


def set_current_task_name(name: str):
    task = asyncio.current_task()
    set_task_name(task, name)


def get_current_task_name():
    try:
        task = asyncio.current_task()
        return get_task_name(task)
    except RuntimeError:
        return 'No Running Loop'


def datagram_supported(loop: asyncio.AbstractEventLoop = None):
    loop = loop or asyncio.get_event_loop()
    return py38 or not isinstance(loop, asyncio.ProactorEventLoop)
