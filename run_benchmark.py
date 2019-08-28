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
from typing import Type


tempdir = mkdtemp()
host = '127.0.0.1'
port = 8888


def protocol_factory_one_way_client() -> StreamClientProtocolFactory:
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject)
    return factory


def tcp_client_one_way():
    return TCPClient(protocol_factory=protocol_factory_one_way_client(), host=host, port=port)


def buffered_file_storage_action() -> BufferedFileStorage:
    action = BufferedFileStorage(base_path=Path(Path(tempdir) / 'Data'), binary=True, close_file_after_inactivity=5,
                                 path='Encoded/{msg.sender}_{msg.name}.{msg.name}')
    return action


def protocol_factory_one_way_server() -> StreamServerProtocolFactory:
    factory = StreamServerProtocolFactory(
        action=buffered_file_storage_action(),
        dataformat=JSONObject)
    return factory


def tcp_server_one_way() -> TCPServer:
    return TCPServer(protocol_factory=protocol_factory_one_way_server(), host=host, port=port)


async def run(num_clients, num_msgs, slow_callback_duration, asyncio_debug):
    loop = asyncio.get_event_loop()
    loop.set_debug(asyncio_debug)
    loop.slow_callback_duration = slow_callback_duration
    json_msg =  b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'
    msgs = [json_msg for _ in range(0, num_msgs)]
    server = tcp_server_one_way()
    server_task = asyncio.create_task(server.start())
    await server.wait_started()
    client = tcp_client_one_way()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        coros = []
        for i in range(0, num_clients):
            override = {'srcip': f'127.0.0.{i + 1}'}
            coro = loop.run_in_executor(executor, client.open_send_msgs, msgs, 0, 1, override)
            coros.append(coro)
        await asyncio.wait(coros)
    await asyncio.wait_for(server.wait_num_has_connected(num_clients), timeout=1000)
    await asyncio.wait_for(server.wait_num_connections(0), timeout=1000)
    await asyncio.wait_for(server.wait_all_tasks_done(), timeout=1000)
    await server.close()
    await server_task


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
        "{msgs.received} {msgs.processed} {received.kb:.2f}KB {processed.kb:.2f}KB {receive_rate.kb:.2f}KB/s {processing_rate.kb:.2f}KB/s {average_buffer_size.kb:.2f}KB {msgs.receive_interval}/s {msgs.processing_time}/s {interval}/s {msgs.buffer_receive_rate}/s {msgs.processing_rate}/s {msgs.buffer_processing_rate}/s {largest_buffer.kb:.2f}KB",
        style="{")


def stats_logging_handler() -> logging.Handler:
    handler = logging_handler_cls()
    handler.setFormatter(stats_formatter())
    return handler


def receiver_debug_logging_extended(level):
    default_level = logging.getLevelName(level)
    main_handler = receiver_logging_handler()
    logger = logging.getLogger('receiver')
    logger.setLevel(default_level)
    logger.addHandler(main_handler)
    logger.propagate = False
    logger = logging.getLogger('sender')
    logger.setLevel(logging.ERROR)
    logger.addHandler(main_handler)
    logger.propagate = False
    actions_logger = logging.getLogger('receiver.actions')
    actions_logger.addHandler(main_handler)
    actions_logger.setLevel(default_level)
    actions_logger.propagate = False
    connection_handler = connection_logging_handler()
    sender_connection_logger = logging.getLogger('sender.connection')
    sender_connection_logger.addHandler(connection_handler)
    sender_connection_logger.propagate = False
    sender_connection_logger.setLevel(logging.ERROR)
    connection_logger = logging.getLogger('receiver.connection')
    logging.getLogger('receiver.raw_received').setLevel(logging.ERROR)
    logging.getLogger('receiver.data_received').setLevel(logging.ERROR)
    logging.getLogger('sender.raw_received').setLevel(logging.ERROR)
    logging.getLogger('sender.data_received').setLevel(logging.ERROR)
    logging.getLogger('sender.raw_sent').setLevel(logging.ERROR)
    connection_logger.addHandler(connection_handler)
    connection_logger.propagate = False
    connection_logger.setLevel(default_level)
    stats_logger = logging.getLogger('receiver.stats')
    stats_logger.addHandler(stats_logging_handler())
    stats_logger.setLevel(logging.INFO)
    stats_logger.propagate = False
    asyncio.get_event_loop().set_debug(True)
    logger = logging.getLogger('asyncio')
    logger.addHandler(main_handler)
    logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clients', default=1, type=int,
                        help='number of clients to send messages with')
    parser.add_argument('-n', '--num', default=1, type=int,
                        help='number of messages')
    parser.add_argument('-l', '--loop', default='selector', type=str,
                        help='loop to use')
    parser.add_argument('-d', '--loglevel', default='ERROR', type=str,
                        help='loop to use')
    parser.add_argument('-a', '--asyncio-debug', action='store_true',
                        help='enable asyncio debug mode')
    parser.add_argument('-s', '--slow-duration', type=float, default=0.1,
                        help='enable asyncio debug mode')
    args, _numeric_placeholders = parser.parse_known_args()
    num_clients = args.clients
    num_msgs = args.num
    loop_type = args.loop
    loglevel = args.loglevel
    scd = args.slow_duration
    asyncio_debug = args.asyncio_debug
    if loop_type:
        set_loop_policy(linux_loop_type=loop_type, windows_loop_type=loop_type)
    receiver_debug_logging_extended(loglevel)
    asyncio.run(run(num_clients, num_msgs, scd, asyncio_debug))
