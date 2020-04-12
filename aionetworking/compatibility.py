import asyncio
import os
import sys
import socket
from typing import Optional, Any, Dict, Coroutine, Set


py39 = sys.version_info >= (3, 9)
py38 = sys.version_info >= (3, 8)
py37 = sys.version_info >= (3, 7)


if py38:
    from typing import Protocol, TypedDict
    from functools import cached_property
else:
    from typing_extensions import Protocol, TypedDict
    from cached_property import cached_property


if py37:
    run = asyncio.run
    create_task = asyncio.create_task
    current_task = asyncio.current_task
    all_tasks = asyncio.all_tasks
    WindowsSelectorEventLoopPolicy = getattr(asyncio, 'WindowsSelectorEventLoopPolicy', None)
    WindowsProactorEventLoopPolicy = getattr(asyncio, 'WindowsProactorEventLoopPolicy', None)

    def net_subnet_of(a, b) -> bool:
        return a.subnet_of(b)

    def net_supernet_of(a, b) -> bool:
        return a.supernet_of(b)

else:
    def _is_subnet_of(a, b):
        try:
            # Always false if one is v4 and the other is v6.
            if a._version != b._version:
                raise TypeError(f"{a} and {b} are not of the same version")
            return (b.network_address <= a.network_address and
                    b.broadcast_address >= a.broadcast_address)
        except AttributeError:
            raise TypeError(f"Unable to test subnet containment "
                            f"between {a} and {b}")


    def net_subnet_of(self, other):
        """Return True if this network is a subnet of other."""
        return _is_subnet_of(self, other)


    def net_supernet_of(self, other):
        """Return True if this network is a supernet of other."""
        return _is_subnet_of(other, self)

    get_running_loop = asyncio.events._get_running_loop

    def create_task(coro: Coroutine) -> asyncio.Task:
        """Schedule the execution of a coroutine object in a spawn task.
        Return a Task object.
        """
        loop = get_running_loop()
        return loop.create_task(coro)

    def current_task() -> asyncio.Task:
        return asyncio.Task.current_task()

    def all_tasks(loop=None) -> Set[asyncio.Task]:
        return asyncio.Task.all_tasks(loop=loop)

    class WindowsSelectorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
        _loop_factory = asyncio.SelectorEventLoop

    if os.name == 'nt':
        class WindowsProactorEventLoopPolicy(asyncio.events.BaseDefaultEventLoopPolicy):
            _loop_factory = asyncio.ProactorEventLoop
    else:
        WindowsProactorEventLoopPolicy = None

    def run(main, *, debug=False):
        """Execute the coroutine and return the result.
        This function runs the passed coroutine, taking care of
        managing the asyncio event loop and finalizing asynchronous
        generators.
        This function cannot be called when another asyncio event loop is
        running in the same thread.
        If debug is True, the event loop will be run in debug mode.
        This function always creates a new event loop and closes it at the end.
        It should be used as a main entry point for asyncio programs, and should
        ideally only be called once.
        Example:
            async def main():
                await asyncio.sleep(1)
                print('hello')
            asyncio.run(main())
        """
        if get_running_loop() is not None:
            raise RuntimeError(
                "asyncio.run() cannot be called from a running event loop")

        if not asyncio.coroutines.iscoroutine(main):
            raise ValueError("a coroutine was expected, got {!r}".format(main))

        loop = asyncio.events.new_event_loop()
        try:
            asyncio.events.set_event_loop(loop)
            loop.set_debug(debug)
            return loop.run_until_complete(main)
        finally:
            try:
                _cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.events.set_event_loop(None)
                loop.close()


    def _cancel_all_tasks(loop):
        to_cancel = all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        loop.run_until_complete(
            asyncio.tasks.gather(*to_cancel, loop=loop, return_exceptions=True))

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler({
                    'message': 'unhandled exception during asyncio.run() shutdown',
                    'exception': task.exception(),
                    'task': task,
                })


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
    task = current_task()
    set_task_name(task, name, include_hierarchy=include_hierarchy, separator=separator)


def get_current_task_name():
    try:
        task = current_task()
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


def get_server_kwargs(ssl_handshake_timeout: bool = None) -> Dict[str, Any]:
    if py37:
        return {'ssl_handshake_timeout': ssl_handshake_timeout}
    return {}


def get_client_kwargs(ssl_handshake_timeout: int = None, happy_eyeballs_delay: Optional[float] = None,
                      interleave: Optional[int] = None) -> Dict[str, Any]:
    kwargs = {}
    if py37:
        if ssl_handshake_timeout:
            kwargs.update({'ssl_handshake_timeout': ssl_handshake_timeout})
    if py38 and is_builtin_loop():
        if happy_eyeballs_delay or interleave:
            kwargs.update({'happy_eyeballs_delay': happy_eyeballs_delay, 'interleave': interleave})
    return kwargs


def default_server_port() -> int:
    loop = asyncio.get_event_loop()
    base_port = 3900 if py39 else 3800 if py38 else 3700
    if os.name == 'nt':
        if isinstance(loop, asyncio.ProactorEventLoop):
            return base_port + 10
        if isinstance(loop, asyncio.SelectorEventLoop):
            return base_port + 11
        return base_port + 12
    if isinstance(loop, asyncio.SelectorEventLoop):
        return base_port
    return base_port + 1


def default_client_port() -> int:
    loop = asyncio.get_event_loop()
    base_port = 39000 if py39 else 38000 if py38 else 37000
    if os.name == 'nt':
        if isinstance(loop, asyncio.ProactorEventLoop):
            return base_port + 100
        if isinstance(loop, asyncio.SelectorEventLoop):
            return base_port + 110
        return base_port + 120
    if isinstance(loop, asyncio.SelectorEventLoop):
        return base_port
    else:
        return base_port + 10
