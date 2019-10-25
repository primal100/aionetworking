from lib.actions.yaml_constructors import load_file_storage, load_buffered_file_storage, load_echo_action
from lib.formats.contrib.yaml_constructors import load_json, load_pickle
from lib.networking.yaml_constructors import (load_server_side_ssl, load_client_side_ssl,
                                              load_stream_server_protocol_factory, load_datagram_server_protocol_factory,
                                              load_stream_client_protocol_factory, load_datagram_client_protocol_factory)
from lib.receivers.yaml_constructors import load_tcp_server, load_udp_server, load_pipe_server
from lib.requesters.yaml_constructors import load_echo_requester
from lib.senders.yaml_constructors import load_tcp_client, load_udp_client, load_pipe_client
from lib.types import load_ip_network, load_path
from .types import load_base_path
from lib.settings import APP_HOME, TEMPDIR

from pathlib import Path
from typing import Union


def load_dir_tags(app_home: Union[str, Path] = APP_HOME):
    load_base_path("!temp", TEMPDIR)
    load_base_path("!conf", app_home / "logs")
    load_base_path("!data", app_home / "logs")
    load_base_path("!logs", app_home / "logs")


def load_minimal_tags():
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
    load_path()
    load_echo_action()
    load_buffered_file_storage()
    load_file_storage()
    load_echo_requester()


def load_all_tags():
    load_minimal_tags()
    from lib.networking.yaml_constructors_sftp import (load_sftp_server_protocol_factory,
                                                       load_sftp_client_protocol_factory)
    from lib.receivers.yaml_constructors_sftp import load_sftp_server
    from lib.senders.yaml_constructors_sftp import load_sftp_client
    load_sftp_server_protocol_factory()
    load_sftp_client_protocol_factory()
    load_sftp_server()
    load_sftp_client()

