import pytest
import os
from pathlib import Path
from lib.conf.yaml_config import load_all_tags, load_paths
import yaml
from tests.test_senders.conftest import *


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
def current_dir() -> Path:
    return Path(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture
def load_all_yaml_tags(tmpdir, current_dir):
    load_all_tags()
    load_paths(app_home=current_dir, volatile_home=tmpdir, tmp_dir=tmpdir)


@pytest.fixture
def conf_dir(current_dir) -> Path:
    return current_dir / "conf"


@pytest.fixture
def stats_dir(current_dir) -> Path:
    return current_dir / "stats"


@pytest.fixture
def data_dir(current_dir) -> Path:
    return current_dir / "data"


@pytest.fixture
def load_conf_dir_tag(conf_dir):
    load_base_path("!conf", Path(conf_dir))


@pytest.fixture
def logs_dir(tmpdir) -> Path:
    return tmpdir / "logs"


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


@pytest.fixture
def server_with_logging_yaml_config_path(conf_dir):
    return conf_dir / "tcp_server_logging.yaml"


@pytest.fixture
def server_with_logging_yaml_config_stream(server_with_logging_yaml_config_path):
    return open(server_with_logging_yaml_config_path, 'r')
