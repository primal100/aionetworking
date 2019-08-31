#!/usr/bin/env python3.7
import asyncio
import concurrent.futures
import argparse
import logging
from pathlib import Path
from lib.actions.file_storage import BufferedFileStorage
from lib.formats.contrib.json import JSONObject
from lib.networking.protocol_factories import StreamServerProtocolFactory, StreamClientProtocolFactory
from lib.receivers.servers import TCPServer
from lib.senders.clients import TCPClient
from lib.utils import set_loop_policy
from tempfile import mkdtemp


host = '127.0.0.1'
port = 8888


def protocol_factory_one_way_client() -> StreamClientProtocolFactory:
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject)
    return factory


def tcp_client_one_way():
    return TCPClient(protocol_factory=protocol_factory_one_way_client(), host=host, port=port)


def buffered_file_storage_action(max_concat) -> BufferedFileStorage:
    tempdir = mkdtemp()
    print(tempdir)
    action = BufferedFileStorage(base_path=Path(Path(tempdir) / 'Data'), binary=True, close_file_after_inactivity=5,
                                 path='Encoded/{msg.sender}_{msg.name}.{msg.name}', max_concat=max_concat)
    return action


def protocol_factory_one_way_server(max_concat) -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        action=buffered_file_storage_action(max_concat),
        dataformat=JSONObject,
    )
    return factory


def tcp_server_one_way(port, max_concat) -> TCPServer:
    return TCPServer(protocol_factory=protocol_factory_one_way_server(max_concat), host=host, port=port)


async def run(num_clients, num_msgs, slow_callback_duration, asyncio_debug, pause_on_size, times, timeout, max_concat):
    loop = asyncio.get_event_loop()
    loop.set_debug(asyncio_debug)
    loop.slow_callback_duration = slow_callback_duration
    json_msg = b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'
    msgs = [json_msg for _ in range(0, num_msgs)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_clients) as executor:
        for i in range(0, times):
            port = 8880 + i
            server = tcp_server_one_way(port, max_concat)
            server_task = asyncio.create_task(server.start())
            await server.wait_started()
            client = tcp_client_one_way()
            coros = []
            for i in range(0, num_clients):
                override = {'srcip': f'127.0.0.{i + 1}', 'port': port}
                coro = loop.run_in_executor(executor, client.open_send_msgs, msgs, 0.000015, 1, override)
                coros.append(coro)
            await asyncio.wait(coros)
            await asyncio.wait_for(server.wait_num_has_connected(num_clients), timeout=timeout)
            await asyncio.wait_for(server.wait_num_connections(0), timeout=timeout)
            await asyncio.wait_for(server.close(), timeout=timeout)
            await asyncio.wait_for(server_task, timeout=timeout)


def logger_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{asctime} - {relativeCreated} - {levelname} - {module} - {funcName} - {name} - {message}", style='{'
    )


def connection_logger_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{asctime} - {relativeCreated} - {levelname} - {taskname} - {module} - {funcName} - {name} - {peer} - {message}", style='{'
    )


def raw_received_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{message}", style='{'
    )


def logging_handler_cls() -> logging.Handler:
    return logging.StreamHandler()


def receiver_logging_handler() -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(logger_formatter())
    return handler


def connection_logging_handler() -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(connection_logger_formatter())
    return handler


def stats_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{msg} {start} {end} {msgs.received} {msgs.processed} {received.kb:.2f}KB {processed.kb:.2f}KB {receive_rate.kb:.2f}KB/s {processing_rate.kb:.2f}KB/s {average_buffer_size.kb:.2f}KB {msgs.receive_interval}/s {msgs.processing_time}/s {interval}/s {msgs.buffer_receive_rate}/s {msgs.processing_rate}/s {msgs.buffer_processing_rate}/s {largest_buffer.kb:.2f}KB",
        style="{")


def sender_stats_formatter() -> logging.Formatter:
    return logging.Formatter(
        "{msg} {msgs.sent} {sent.kb:.2f}KB {send_rate.kb:.2f}KB/s {msgs.send_rate:.2f}/s {msgs.send_interval}/s {interval}/s",
        style="{")


def sender_stats_handler() -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(sender_stats_formatter())
    return handler


def stats_logging_handler() -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(stats_formatter())
    return handler


def setup_logging(level, sender_loglevel):
    receiver_level = logging.getLevelName(level)
    sender_loglevel = logging.getLevelName(sender_loglevel)
    main_handler = receiver_logging_handler()
    logger = logging.getLogger('receiver')
    logger.setLevel(receiver_level)
    logger.addHandler(main_handler)
    logger.propagate = False
    sender_logger = logging.getLogger('sender')
    sender_logger.setLevel(sender_loglevel)
    sender_logger.addHandler(main_handler)
    sender_logger.propagate = False
    actions_logger = logging.getLogger('receiver.actions')
    actions_logger.addHandler(main_handler)
    actions_logger.setLevel(receiver_level)
    actions_logger.propagate = False
    connection_handler = connection_logging_handler()
    sender_connection_logger = logging.getLogger('sender.connection')
    sender_connection_logger.addHandler(connection_handler)
    sender_connection_logger.propagate = False
    sender_connection_logger.setLevel(sender_loglevel)
    connection_logger = logging.getLogger('receiver.connection')
    logging.getLogger('receiver.raw_received').setLevel(logging.ERROR)
    logging.getLogger('receiver.data_received').setLevel(logging.ERROR)
    logging.getLogger('sender.raw_received').setLevel(logging.ERROR)
    logging.getLogger('sender.data_received').setLevel(logging.ERROR)
    logging.getLogger('sender.raw_sent').setLevel(logging.ERROR)
    connection_logger.addHandler(connection_handler)
    connection_logger.propagate = False
    connection_logger.setLevel(receiver_level)
    stats_logger = logging.getLogger('receiver.stats')
    stats_logger.addHandler(stats_logging_handler())
    stats_logger.setLevel(logging.ERROR)
    stats_logger.propagate = False
    sender_stats_logger = logging.getLogger('sender.stats')
    sender_stats_logger.addHandler(sender_stats_handler())
    sender_stats_logger.setLevel(logging.INFO)
    sender_stats_logger.propagate = False
    logger = logging.getLogger('asyncio')
    logger.addHandler(main_handler)
    logger.setLevel(level)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clients', default=1, type=int,
                        help='number of clients to send messages with')
    parser.add_argument('-n', '--num', default=1, type=int,
                        help='number of messages'),
    parser.add_argument('-i', '--times', type=int, default=1,
                        help='number of times to run benchmark')
    parser.add_argument('-p', '--pause_on_size', default=None, type=int,
                        help='Pause Reading on transport on buffer size')
    parser.add_argument('-l', '--loop', default='selector', type=str,
                        help='loop to use')
    parser.add_argument('-t', '--timeout', default=5, type=int,
                        help='timeout for benchmark wait_for')
    parser.add_argument('-r', '--loglevel', default='ERROR', type=str,
                        help='receiver log level')
    parser.add_argument('-s', '--senderloglevel', default='ERROR', type=str,
                        help='sender log level')
    parser.add_argument('-a', '--asyncio-debug', action='store_true',
                        help='enable asyncio debug mode')
    parser.add_argument('-d', '--slow-duration', type=float, default=0.1,
                        help='asyncio slow_callback_duration paramater')
    parser.add_argument('-m', '--max-concat', type=int, default=1000,
                        help='max items to concat in file storage action')
    args, _numeric_placeholders = parser.parse_known_args()
    num_clients = args.clients
    num_msgs = args.num
    times = args.times
    pause_on_size = args.pause_on_size
    loop_type = args.loop
    loglevel = args.loglevel
    sender_loglevel = args.senderloglevel
    timeout = args.timeout
    scd = args.slow_duration
    max_concat = args.max_concat
    asyncio_debug = args.asyncio_debug
    if loop_type:
        set_loop_policy(linux_loop_type=loop_type, windows_loop_type=loop_type)
    setup_logging(loglevel, sender_loglevel)
    asyncio.run(run(num_clients, num_msgs, scd, asyncio_debug, pause_on_size, times, timeout, max_concat))
