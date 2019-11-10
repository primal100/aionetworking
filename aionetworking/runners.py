import asyncio
import os
from .conf.yaml_config import SignalServerManager, load_all_tags, server_from_config_file
from typing import Union, Dict
from pathlib import Path


async def run_until_signal(conf: Union[str, Path], paths: Dict[str, Union[str, Path]] = None, notify_pid: int = None):
    manager = SignalServerManager(conf, paths=paths, notify_pid=notify_pid)
    await manager.serve_until_stopped()


async def run_forever(conf, paths: Dict[str, Union[str, Path]] = None):
    server = server_from_config_file(conf, paths=paths)
    await server.serve_forever()


def run_server(conf_file, paths: Dict[str, Union[str, Path]] = None, asyncio_debug: bool = False,
               notify_pid: int = None):
    if os.name == 'posix':
        asyncio.run(run_until_signal(conf_file, paths=paths, notify_pid=notify_pid), debug=asyncio_debug)
    else:
        try:
            asyncio.run(run_forever(conf_file, paths=paths), debug=asyncio_debug)
        except KeyboardInterrupt:
            pass


def run_server_default_tags(conf_file, paths: Dict[str, Union[str, Path]] = None, asyncio_debug: bool = False,
                            notify_pid: int = None):
    load_all_tags()
    run_server(conf_file, paths=paths, asyncio_debug=asyncio_debug, notify_pid=notify_pid)
