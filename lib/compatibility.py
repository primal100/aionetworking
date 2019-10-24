import asyncio
import sys


py38 = sys.version_info >= (3, 8)


if py38:
    from typing import Protocol, TypedDict
    from functools import cached_property
else:
    from typing_extensions import Protocol, TypedDict
    from cached_property import cached_property


def set_task_name(task: asyncio.Future, name: str, include_hierarchy: bool = True, separator: str = ':'):
    if hasattr(task, "set_name"):
        task_name = get_task_name(task)
        name = f"{task_name}_{name}" if name else task_name
        if include_hierarchy:
            prefix = get_current_task_name()
            if any(prefix == text for text in ("No Running Loop", "No Task")):
                prefix = ''
            prefix += task_name
            name = f"{prefix}{separator}{name}" if prefix else name
        task.set_name(name)


def get_task_name(task: asyncio.Future) -> str:
    if hasattr(task, "get_name"):
        return task.get_name()
    return str(id(task))


def set_current_task_name(name: str, include_hierarchy: bool = True, separator: str = ':'):
    task = asyncio.current_task()
    set_task_name(task, name, include_hierarchy=include_hierarchy, separator=separator)


def get_current_task_name():
    try:
        task = asyncio.current_task()
        if task:
            return get_task_name(task)
        return "No Task"
    except RuntimeError:
        return 'No Running Loop'


def is_proactor(loop: asyncio.AbstractEventLoop = None):
    if not hasattr(asyncio, "ProactorEventLoop"):
        return True
    loop = loop or asyncio.get_event_loop()
    return isinstance(loop, asyncio.ProactorEventLoop)


def datagram_supported(loop: asyncio.AbstractEventLoop = None):
    return py38 or not is_proactor(loop=loop)
