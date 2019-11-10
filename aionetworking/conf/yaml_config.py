from __future__ import annotations
import asyncio
import yaml
import os
from dataclasses import dataclass, field
import sys

from logging.config import dictConfig
from aionetworking.actions.yaml_constructors import load_file_storage, load_buffered_file_storage, load_echo_action, \
    load_empty_action
from aionetworking.compatibility_os import loop_on_close_signal, loop_on_user1_signal, send_stopping, send_status, \
    send_ready, send_reloading
from aionetworking.conf.yaml_constructors import load_logger, load_receiver_logger, load_sender_logger
from aionetworking.formats.contrib.yaml_constructors import load_json, load_pickle
from aionetworking.networking.yaml_constructors import (load_server_side_ssl, load_client_side_ssl,
                                                        load_stream_server_protocol_factory,
                                                        load_datagram_server_protocol_factory,
                                                        load_stream_client_protocol_factory,
                                                        load_datagram_client_protocol_factory)
from aionetworking.types.receivers import ReceiverType
from aionetworking.receivers.yaml_constructors import load_tcp_server, load_udp_server, load_pipe_server
from aionetworking.requesters.yaml_constructors import load_echo_requester
from aionetworking.types.senders import SenderType
from aionetworking.senders.yaml_constructors import load_tcp_client, load_udp_client, load_pipe_client
from .yaml_constructors import load_ip_network, load_path
from aionetworking.settings import APP_HOME, TEMPDIR

import time
from pathlib import Path
from typing import Union, Dict, TextIO


def get_paths(app_home: Union[str, Path] = APP_HOME, volatile_home: Union[str, Path] = None,
               tmp_dir: Union[str, Path] = TEMPDIR) -> Dict[str, Path]:
    volatile_home = volatile_home or app_home
    return {'temp': tmp_dir,
            'home': app_home,
            'conf': app_home / 'conf',
            'data': volatile_home / 'data',
            'logs': volatile_home / 'logs',
            'misc': volatile_home / 'misc',
            'stats': volatile_home / 'stats',
            'ssl': app_home / 'ssl'}


def load_minimal_tags() -> None:
    load_logger()
    load_receiver_logger()
    load_sender_logger()
    load_tcp_server()
    load_tcp_client()
    load_udp_server()
    load_udp_client()
    load_pipe_server()
    load_pipe_client()
    load_server_side_ssl()
    load_client_side_ssl()
    load_stream_server_protocol_factory()
    load_datagram_server_protocol_factory()
    load_stream_client_protocol_factory()
    load_datagram_client_protocol_factory()
    load_json()
    load_pickle()
    load_ip_network()
    load_echo_action()
    load_empty_action()
    load_buffered_file_storage()
    load_file_storage()
    load_echo_requester()


def load_all_tags():
    load_minimal_tags()
    from aionetworking.networking.yaml_constructors_sftp import (load_sftp_server_protocol_factory,
                                                       load_sftp_client_protocol_factory)
    from aionetworking.receivers.yaml_constructors_sftp import load_sftp_server
    from aionetworking.senders.yaml_constructors_sftp import load_sftp_client
    load_sftp_server_protocol_factory()
    load_sftp_client_protocol_factory()
    load_sftp_server()
    load_sftp_client()


def configure_logging(path: Path):
    with path.open('rt') as f:
        config = yaml.safe_load(f.read())
        for handler in config['handlers'].values():
            filename = handler.get('filename')
            if filename:
                filename.parent.mkdir(parents=True, exist_ok=True)
        dictConfig(config)


def node_from_file(path: Union[str, Path], paths: Dict[str, Union[str, Path]] = None) -> \
        Union[ReceiverType, SenderType]:
    stream = open(path, 'r')
    return node_from_config(stream, paths=paths)


def node_from_config(conf: TextIO, paths: Dict[str, Union[str, Path]] = None) -> \
        Union[ReceiverType, SenderType]:
    paths = paths or get_paths()
    load_path(paths)
    configs = list(yaml.safe_load_all(conf))
    node = configs[0]
    if len(configs) > 1:
        misc_config = configs[1]
        log_config_file = misc_config['log_config_file']
        node_name = misc_config.get('node_name')
        if not node_name:
            node_name = node.full_name.replace(' ', '_')
        paths['node'] = node_name
        paths['name'] = node.name.replace(' ', '_')
        paths['host'] = node.host
        paths['port'] = node.port
        paths['pid'] = str(os.getpid())
        configure_logging(log_config_file)
    return node


def node_from_config_file(conf_path: Union[Path, str], paths: Dict[str, Union[str, Path]] = None) -> Union[ReceiverType, SenderType]:
    f = open(str(conf_path), 'r')
    return node_from_config(f, paths=paths)


def server_from_config_file(conf_path: Union[Path, str], paths: Dict[str, Union[str, Path]] = None) -> ReceiverType:
    return node_from_config_file(conf_path, paths=paths)


def client_from_config_file(conf_path: Union[Path, str], paths: Dict[str, Union[str, Path]] = None) -> SenderType:
    return node_from_config_file(conf_path, paths=paths)


@dataclass
class SignalServerManager:
    conf_path: Union[Path, str]
    server: ReceiverType = field(init=False)
    _last_modified_time: float = field(init=False, default=None)
    paths: Dict[str, Union[str, Path]] = None

    def __post_init__(self):
        self._last_modified_time = self.modified_time
        self._stop_event = asyncio.Event()
        self._restart_event = asyncio.Event()
        self._restart_event.set()
        self.server = self.get_server()
        loop_on_close_signal(self.close)
        loop_on_user1_signal(self.check_reload)

    @property
    def modified_time(self) -> float:
        return os.stat(self.conf_path).st_mtime

    def close(self) -> None:
        send_stopping()
        send_status('Stopping server')
        self._stop_event.set()

    def check_reload(self) -> None:
        if os.path.exists(self.conf_path):
            last_modified = self.modified_time
            if last_modified > self._last_modified_time:
                send_reloading()
                self._last_modified_time = last_modified
                send_status('Restarting server')
                self._restart_event.set()
                self._stop_event.set()
            else:
                send_ready()
        else:
            self._stop_event.set()

    def server_is_started(self):
        return self.server.is_started

    async def wait_server_stopped(self):
        await self.server.wait_stopped()

    async def wait_server_started(self):
        await self.server.wait_started()

    def get_server(self) -> ReceiverType:
        return server_from_config_file(self.conf_path, self.paths)

    async def serve_until_stopped(self) -> None:
        while self._restart_event.is_set():
            self._restart_event.clear()
            self._stop_event.clear()
            await self.server.serve_until_close_signal(stop_event=self._stop_event)
            if self._restart_event.is_set():
                self.server = self.get_server()
