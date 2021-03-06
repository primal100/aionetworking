from tests.test_07_end_to_end.conftest import *
import pytest
import yaml
import shutil
import logging.config

from aionetworking.compatibility import create_task
from aionetworking.logging import PeerFilter, MessageFilter, Logger, ConnectionLogger, ConnectionLoggerStats, StatsTracker, StatsLogger
from aionetworking.conf import load_all_tags, get_paths, SignalServerManager
from aionetworking.receivers import TCPServer
from aionetworking.types.networking import AFINETContext
from aionetworking.utils import Expression
import asyncio

from pathlib import Path
from typing import Any, Dict


@pytest.fixture
def reset_logging():
    logger = logging.getLogger()
    yield
    logger.manager.loggerDict = {}


@pytest.fixture
def tcp_server_one_way_yaml_config_path(conf_dir) -> Path:
    return conf_dir / "tcp_server_oneway.yaml"


@pytest.fixture
def logging_yaml_path(conf_dir) -> Path:
    return conf_dir / "logging.yaml"


@pytest.fixture
def tcp_server_one_way_yaml_with_env_config_path(conf_dir) -> Path:
    return conf_dir / "tcp_server_oneway_with_env.yaml"


@pytest.fixture
async def tcp_server_one_way_env_ip(protocol_factory_server) -> TCPServer:
    env_ip = '10.10.10.10'
    os.environ['IP'] = str(env_ip)
    server = TCPServer(protocol_factory=protocol_factory_server, host=env_ip, port=0)
    yield server


@pytest.fixture
def tcp_client_one_way_yaml_config_path(conf_dir):
    return conf_dir / "tcp_client_one_way.yaml"


@pytest.fixture
def tcp_server_two_way_ssl_yaml_config_path(conf_dir):
    return conf_dir / "tcp_server_two_way_ssl.yaml"


@pytest.fixture
def tcp_client_two_way_ssl_yaml_config_path(conf_dir):
    return conf_dir / "tcp_client_two_way_ssl.yaml"


@pytest.fixture
def udp_server_yaml_config_path(conf_dir):
    return conf_dir / "udp_server.yaml"


@pytest.fixture
def pipe_server_yaml_config_path(conf_dir, server_pipe_address_load):
    return conf_dir / "pipe_server.yaml"


@pytest.fixture
def pipe_client_yaml_config_path(conf_dir, server_pipe_address_load):
    return conf_dir / "pipe_client.yaml"


@pytest.fixture
def sftp_server_yaml_config_path(conf_dir):
    return conf_dir / "sftp_server.yaml"


@pytest.fixture
def sftp_client_yaml_config_path(conf_dir):
    return conf_dir / "sftp_client.yaml"


@pytest.fixture
def test_config_dir() -> Path:
    return Path(os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture
def all_paths(tmpdir, test_config_dir, ssl_dir) -> Dict[str, Any]:
    return get_paths(app_home=test_config_dir, volatile_home=tmpdir, temp=tmpdir,
                     ssl=ssl_dir)


@pytest.fixture
def conf_dir(all_paths) -> Path:
    return all_paths['conf']


@pytest.fixture
def load_all_yaml_tags():
    load_all_tags()


@pytest.fixture
def new_event_loop():
    yield
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


@pytest.fixture
def server_pipe_address_load(pipe_path):
    def pipe_address_constructor(loader, node) -> Path:
        if node.value:
            value = loader.construct_yaml_int(node)
            if value:
                return value
        return pipe_path

    yaml.add_constructor('!PipeAddr', pipe_address_constructor, Loader=yaml.SafeLoader)


@pytest.fixture
def config_file(conf_dir, connection_type, endpoint, duplex_type):
    filename = f'{connection_type}_{endpoint}_{duplex_type}.yaml'
    return conf_dir / filename


@pytest.fixture
def config_file_stream(config_file):
    return open(config_file, 'r')


@pytest.fixture
def expected_object(server, client_fixed_port, endpoint):
    return server if endpoint == 'server' else client_fixed_port


@pytest.fixture
def peer_filter(client_sock) -> PeerFilter:
    return PeerFilter([client_sock[0]])


@pytest.fixture
def message_filter() -> MessageFilter:
    return MessageFilter(Expression.from_string("method == login"))


@pytest.fixture()
def log_record(client_sock_str, server_sock_str) -> logging.LogRecord:
    record = logging.LogRecord('receiver.connection', logging.INFO, os.path.abspath(__file__), 180,
                               'New %s connection from %s to %s', ('TCP Server', client_sock_str, server_sock_str),
                               None, func='new_connection', sinfo=None)
    record.hostname = 'localhost'
    record.host = '127.0.0.1'
    return record


@pytest.fixture()
def log_record_not_included(client_sock, server_sock_str, client_sock_ipv6) -> logging.LogRecord:
    record = logging.LogRecord('receiver.connection', logging.INFO, os.path.abspath(__file__), 180,
                               'New %s connection from %s to %s', ('TCP Server', f'{client_sock_ipv6[0]}:{client_sock[1]}',
                                                                   server_sock_str),
                               None, func='new_connection', sinfo=None)
    record.hostname = 'localhost2'
    record.host = client_sock_ipv6[0]
    return record


@pytest.fixture()
def log_record_msg_object(json_rpc_login_request_object) -> logging.LogRecord:
    record = logging.LogRecord('receiver.msg_received', logging.DEBUG, os.path.abspath(__file__), 180,
                               'MSG RECEIVED', (), None, func='_msg_received', sinfo=None)
    record.msg_obj = json_rpc_login_request_object
    return record


@pytest.fixture()
def log_record_msg_object_not_included(json_rpc_logout_request_object) -> logging.LogRecord:
    record = logging.LogRecord('receiver.msg_received', logging.DEBUG, os.path.abspath(__file__), 180,
                               'MSG RECEIVED', (), None, func='_msg_received', sinfo=None)
    record.msg_obj = json_rpc_logout_request_object
    return record


@pytest.fixture
async def receiver_connection_logger(receiver_logger, tcp_server_context_fixed_port, caplog) -> ConnectionLogger:
    caplog.set_level(logging.DEBUG, "receiver.connection")
    caplog.set_level(logging.DEBUG, "receiver.msg_received")
    caplog.set_level(logging.ERROR, "receiver.stats")
    yield receiver_logger.get_connection_logger(extra=tcp_server_context_fixed_port)
    caplog.set_level(logging.ERROR, "receiver.connection")
    caplog.set_level(logging.ERROR, "receiver.msg_received")


@pytest.fixture
def context_wrong_peer(client_sock, client_sock_str, client_hostname, server_sock, server_sock_str) -> AFINETContext:
    client_sock = ('127.0.0.2', client_sock[1])
    client_sock_str = f'127.0.0.2:{client_sock[1]}'
    context: AFINETContext = {
        'protocol_name': 'TCP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str, 'client': client_sock_str,
        'own': server_sock_str, 'address': client_sock[0]
    }
    return context


@pytest.fixture
async def receiver_connection_logger_wrong_peer(receiver_logger, context_wrong_peer, caplog) -> ConnectionLogger:
    caplog.set_level(logging.DEBUG, "receiver.connection")
    caplog.set_level(logging.DEBUG, "receiver.msg_received")
    yield receiver_logger.get_connection_logger(extra=context_wrong_peer)
    caplog.set_level(logging.ERROR, "receiver.connection")
    caplog.set_level(logging.ERROR, "receiver.msg_received")


@pytest.fixture
def sender_logger() -> Logger:
    return Logger('sender')


@pytest.fixture
def sender_connection_logger(sender_logger, tcp_client_context_fixed_port) -> ConnectionLogger:
    return sender_logger.get_connection_logger(extra=tcp_client_context_fixed_port)


@pytest.fixture
async def receiver_connection_logger_stats(receiver_logger, context, caplog) -> ConnectionLoggerStats:
    caplog.set_level(logging.INFO, "receiver.stats")
    caplog.set_level(logging.DEBUG, "receiver.connection")
    caplog.set_level(logging.DEBUG, "receiver.msg_received")
    logger = receiver_logger.get_connection_logger(extra=context)
    yield logger
    if not logger.is_closing:
        logger.connection_finished()
    await logger.wait_closed()
    caplog.set_level(logging.ERROR, "receiver.msg_received")
    caplog.set_level(logging.ERROR, "receiver.stats")
    caplog.set_level(logging.ERROR, "receiver.connection")


@pytest.fixture
def debug_logging(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    yield
    caplog.set_level(logging.ERROR)


@pytest.fixture
def zero_division_exception() -> BaseException:
    try:
        1 / 0
    except ZeroDivisionError as e:
        return e


@pytest.fixture(params=['', 'stats'])
async def connection_logger(request, receiver_connection_logger, receiver_connection_logger_stats):
    if request.param == 'stats':
        yield receiver_connection_logger_stats
    else:
        yield receiver_connection_logger


@pytest.fixture
def critical_connection_logging_debug_received_logging(caplog):
    connection_level = logging.getLogger('receiver.connection').level
    msg_received_level = logging.getLogger('receiver.connection').level
    logging.getLogger('receiver.connection').setLevel(logging.CRITICAL)
    logging.getLogger('receiver.msg_received').setLevel(logging.DEBUG)
    yield
    logging.getLogger('receiver.connection').setLevel(connection_level)
    logging.getLogger('receiver.msg_received').setLevel(msg_received_level)


@pytest.fixture
def logging_handler_with_msg_obj_uid_formatter(caplog):
    default_formatter = caplog.handler.formatter
    caplog.handler.setFormatter(logging.Formatter("{msg_obj.uid}", style='{'))
    yield
    caplog.handler.setFormatter(default_formatter)


@pytest.fixture
def stats_tracker() -> StatsTracker:
    return StatsTracker()


@pytest.fixture
async def stats_logger(context) -> StatsLogger:
    logger = StatsLogger("receiver.stats", extra=context, stats_interval=0.1, stats_fixed_start_time=False)
    yield logger
    if not logger.is_closing:
        logger.connection_finished()
    await logger.wait_closed()


@pytest.fixture
def stats_formatter() -> logging.Formatter:
    # noinspection PyPep8
    return logging.Formatter(
        "{peer} {msg} {msgs.received} {msgs.processed} {received.kb:.2f}KB {processed.kb:.2f}KB {receive_rate.kb:.2f}KB/s {processing_rate.kb:.2f}KB/s {average_buffer_size.kb:.2f}KB {msgs.receive_interval}/s {msgs.processing_time}/s {msgs.buffer_receive_rate}/s {msgs.processing_rate}/s {msgs.buffer_processing_rate}/s {largest_buffer.kb:.2f}KB",
        style="{")


@pytest.fixture
def tmp_config_file(tmp_path, tcp_server_one_way_yaml_config_path, logging_yaml_path, load_all_yaml_tags) -> Path:
    path = tmp_path / tcp_server_one_way_yaml_config_path.name
    shutil.copy(str(tcp_server_one_way_yaml_config_path), str(path))
    logging_path = tmp_path / logging_yaml_path.name
    shutil.copy(str(logging_yaml_path), str(logging_path))
    return path


@pytest.fixture
async def signal_server_manager(tmp_config_file) -> SignalServerManager:
    server_manager = SignalServerManager(tmp_config_file)
    yield server_manager
    server_manager.close()


@pytest.fixture
async def signal_server_manager_started(tmp_config_file) -> SignalServerManager:
    server_manager = SignalServerManager(tmp_config_file)
    task = create_task(server_manager.serve_until_stopped())
    await server_manager.wait_server_started()
    yield server_manager
    server_manager.close()
    await server_manager.wait_server_stopped()
    await task

