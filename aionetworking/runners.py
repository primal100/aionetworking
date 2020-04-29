import asyncio
import os
from aionetworking.compatibility import run
from .conf.yaml_config import SignalServerManager, load_all_tags, server_from_config_file
from typing import Union, Dict
from pathlib import Path


async def run_until_signal(conf: Union[str, Path], paths: Dict[str, Union[str, Path]] = None, notify_pid: int = None,
                           duration: int = None):
    manager = SignalServerManager(conf, paths=paths, notify_pid=notify_pid)
    try:
        await asyncio.wait_for(manager.serve_until_stopped(), timeout=duration)
    except asyncio.TimeoutError:
        pass


async def run_forever(conf, paths: Dict[str, Union[str, Path]] = None, duration: int = None):
    server = server_from_config_file(conf, paths=paths)
    try:
        await asyncio.wait_for(server.serve_forever(), timeout=duration)
    except asyncio.TimeoutError:
        pass


def run_server(conf_file, paths: Dict[str, Union[str, Path]] = None, asyncio_debug: bool = False,
               notify_pid: int = None, duration: int = None):
    debug = asyncio_debug or asyncio.coroutines._DEBUG
    if os.name == 'posix':
        run(run_until_signal(conf_file, paths=paths, notify_pid=notify_pid, duration=duration),
                        debug=debug)
    else:
        try:
            run(run_forever(conf_file, paths=paths, duration=duration), debug=debug)
        except (KeyboardInterrupt, asyncio.TimeoutError):
            pass


def run_server_default_tags(conf_file, paths: Dict[str, Union[str, Path]] = None, asyncio_debug: bool = False,
                            notify_pid: int = None, duration: int = None):
    load_all_tags()
    run_server(conf_file, paths=paths, asyncio_debug=asyncio_debug, notify_pid=notify_pid, duration=duration)
