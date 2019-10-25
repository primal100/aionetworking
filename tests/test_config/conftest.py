import pytest
import os
from pathlib import Path
from lib.types import load_base_path
from lib.yaml_constructors import load_all_tags
import yaml
from tests.test_senders.conftest import *


@pytest.fixture
def conf_dir() -> Path:
    return Path(os.path.abspath(os.path.dirname(__file__))) / "conf"


@pytest.fixture
def tcp_server_one_way_yaml_config_path(conf_dir):
    return conf_dir / "tcp_server_one_way.yaml"


@pytest.fixture
def tcp_server_one_way_yaml_config_stream(tcp_server_one_way_yaml_config_path):
    return open(tcp_server_one_way_yaml_config_path, 'r')


@pytest.fixture
def tcp_client_one_way_yaml_config_path(conf_dir):
    return conf_dir / "tcp_client_one_way.yaml"


@pytest.fixture
def tcp_client_one_way_yaml_config_stream(tcp_client_one_way_yaml_config_path):
    return open(tcp_client_one_way_yaml_config_path, 'r')


@pytest.fixture
def tcp_server_two_way_ssl_yaml_config_path(conf_dir):
    return conf_dir / "tcp_server_two_way_ssl.yaml"


@pytest.fixture
def tcp_server_two_way_ssl_yaml_config_stream(tcp_server_two_way_ssl_yaml_config_path):
    return open(tcp_server_two_way_ssl_yaml_config_path, 'r')


@pytest.fixture
def tcp_client_two_way_ssl_yaml_config_path(conf_dir):
    return conf_dir / "tcp_client_two_way_ssl.yaml"


@pytest.fixture
def tcp_client_two_way_ssl_yaml_config_stream(tcp_client_two_way_ssl_yaml_config_path):
    return open(tcp_client_two_way_ssl_yaml_config_path, 'r')


@pytest.fixture
def udp_server_yaml_config_path(conf_dir):
    return conf_dir / "udp_server.yaml"


@pytest.fixture
def udp_server_yaml_config_stream(udp_server_yaml_config_path):
    return open(udp_server_yaml_config_path, 'r')


@pytest.fixture
def pipe_server_yaml_config_path(conf_dir):
    return conf_dir / "pipe_server.yaml"


@pytest.fixture
def pipe_server_yaml_config_stream(pipe_server_yaml_config_path):
    return open(pipe_server_yaml_config_path, 'r')


@pytest.fixture
def pipe_client_yaml_config_path(conf_dir):
    return conf_dir / "pipe_client.yaml"


@pytest.fixture
def pipe_client_yaml_config_stream(pipe_client_yaml_config_path):
    return open(pipe_client_yaml_config_path, 'r')


@pytest.fixture
def sftp_server_yaml_config_path(conf_dir):
    return conf_dir / "sftp_server.yaml"


@pytest.fixture
def sftp_server_yaml_config_stream(sftp_server_yaml_config_path):
    return open(sftp_server_yaml_config_path, 'r')


@pytest.fixture
def sftp_client_yaml_config_path(conf_dir):
    return conf_dir / "sftp_client.yaml"


@pytest.fixture
def sftp_client_yaml_config_stream(sftp_client_yaml_config_path):
    return open(sftp_client_yaml_config_path, 'r')


@pytest.fixture
def load_all_yaml_tags():
    load_all_tags()


@pytest.fixture
def load_tmp_dir_tag(tmpdir):
    load_base_path("!TmpDir", Path(tmpdir))


@pytest.fixture
def load_ssl_dir_tag(ssl_dir):
    load_base_path("!SSLDir", Path(ssl_dir))


@pytest.fixture
def server_port_load(sock):
    def port_constructor(loader, node) -> int:
        if node.value:
            value = loader.construct_yaml_int(node)
            if value:
                return value
        return sock[1]

    yaml.add_constructor('!Port', port_constructor, Loader=yaml.SafeLoader)


@pytest.fixture
def server_pipe_address_load(pipe_path):
    def pipe_address_constructor(loader, node) -> Path:
        if node.value:
            value = loader.construct_yaml_int(node)
            if value:
                return value
        return pipe_path

    yaml.add_constructor('!PipeAddr', pipe_address_constructor, Loader=yaml.SafeLoader)


@pytest.fixture(params=[
        lazy_fixture(
            (tcp_server_one_way_yaml_config_stream.__name__, tcp_server_one_way.__name__)),
        lazy_fixture(
            (tcp_client_one_way_yaml_config_stream.__name__, tcp_client_one_way.__name__)),
        lazy_fixture(
            (tcp_server_two_way_ssl_yaml_config_stream.__name__, tcp_server_two_way_ssl.__name__)),
        lazy_fixture(
            (tcp_client_two_way_ssl_yaml_config_stream.__name__, tcp_client_two_way_ssl_no_cadata.__name__)),
        lazy_fixture(
            (udp_server_yaml_config_stream.__name__, udp_server_allowed_senders_ipv4.__name__)),
        lazy_fixture(
            (pipe_server_yaml_config_stream.__name__, pipe_server_two_way.__name__)),
        lazy_fixture(
            (pipe_client_yaml_config_stream.__name__, pipe_client_two_way.__name__)),
        lazy_fixture(
            (sftp_server_yaml_config_stream.__name__, sftp_server.__name__)),
        lazy_fixture(
            (sftp_client_yaml_config_stream.__name__, sftp_client.__name__))
])
def config_files_args(request):
    return request.param


@pytest.fixture
def config_file(config_files_args):
    return config_files_args[0]


@pytest.fixture
def expected_object(config_files_args):
    return config_files_args[1]