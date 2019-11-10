from __future__ import annotations
import asyncio
import os
import sys
import socket
from typing import Optional, Any, Dict


py39 = sys.version_info >= (3, 9)
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
        return False
    loop = loop or asyncio.get_event_loop()
    return isinstance(loop, asyncio.ProactorEventLoop)


def datagram_supported(loop: asyncio.AbstractEventLoop = None):
    return py38 or not is_proactor(loop=loop)


def supports_pipe_or_unix_connections() -> bool:
    return hasattr(socket, 'AF_UNIX') or hasattr(asyncio.get_event_loop(), 'start_serving_pipe')


def supports_pipe_or_unix_connections_in_other_process() -> bool:
    if not supports_pipe_or_unix_connections():
        return False
    if not py38 and os.name == 'nt':
        return False
    return True


def is_selector():
    return type(asyncio.get_event_loop()) == asyncio.SelectorEventLoop


def is_builtin_loop() -> bool:
    return is_selector() or is_proactor()


def supports_keyboard_interrupt() -> bool:
    return os.name != 'nt' or (py38 and is_proactor())


def get_client_kwargs(happy_eyeballs_delay: Optional[float] = None, interleave: Optional[int] = None) -> Dict[str, Any]:
    if py38 and is_builtin_loop():
        return {'happy_eyeballs_delay': happy_eyeballs_delay, 'interleave': interleave}
    return {}


def default_server_port() -> int:
    loop = asyncio.get_event_loop()
    base_port = 3900 if py39 else 3800 if py38 else 3700
    if os.name == 'nt':
        if isinstance(loop, asyncio.ProactorEventLoop):
            return base_port + 10
        if isinstance(loop, asyncio.SelectorEventLoop):
            return base_port + 15
    if isinstance(loop, asyncio.SelectorEventLoop):
        return base_port
    else:
        return base_port + 5


def default_client_port() -> int:
    loop = asyncio.get_event_loop()
    base_port = 39000 if py39 else 38000 if py38 else 37000
    if os.name == 'nt':
        if isinstance(loop, asyncio.ProactorEventLoop):
            return base_port + 100
        if isinstance(loop, asyncio.SelectorEventLoop):
            return base_port + 150
    if isinstance(loop, asyncio.SelectorEventLoop):
        return base_port
    else:
        return base_port + 50