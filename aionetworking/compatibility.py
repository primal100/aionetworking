from __future__ import annotations
import asyncio
import sys
import socket


py38 = sys.version_info >= (3, 8)


if py38:
    from typing import Protocol, TypedDict
    from functools import cached_property
else:
    from typing_extensions import Protocol, TypedDict
    from cached_property import cached_property


def supports_task_name():
    return hasattr(asyncio.Task, 'get_name')


def set_task_name(task: asyncio.Task, name: str, include_hierarchy: bool = True, separator: str = ':'):
    if hasattr(task, "set_name"):
        task_name = get_task_name(task)
        new_name = f"{task_name}_{name}" if name else task_name
        if include_hierarchy:
            prefix = get_current_task_name()
            if any(prefix == text for text in ("No Running Loop", "No Task", task_name)):
                prefix = ''
            new_name = f"{prefix}{separator}{new_name}" if prefix else new_name
        task.set_name(new_name)


def get_task_name(task: asyncio.Task) -> str:
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


def supports_pipe_or_unix_connections() -> bool:
    return hasattr(socket, 'AF_UNIX') or hasattr(asyncio.get_event_loop(), 'start_serving_pipe')