import asyncio
from functools import partial
from datetime import datetime
import binascii
import logging

from lib import messagemanagers
from lib.counters import TaskCounter
from lib.utils import Record, plural
from .logging import ConnectionLogger, StatsLogger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseProtocolMixin:
    stats_cls = StatsLogger
    name: str = ''
    logger_name: str = ''
    logger: None
    stats_logger = None
    alias: str = ''
    peer: str = ''
    sock = (None, None)
    own: str = ''
    peer_ip: str = None
    peer_port: int = 0
    transport = None

    @classmethod
    def with_config(cls, logger, cp=None, **kwargs):
        from lib import settings
        cp = cp or settings.CONFIG
        connection_logger = logging.getLogger(f'{logger.name}.connection')
        stats_logger_cls = cls.stats_cls.with_config(logger, cp=cp)
        return partial(cls, logger=connection_logger, stats_logger_cls=stats_logger_cls, **kwargs)

    def __init__(self, manager: BaseMessageManager, logger=None, stats_logger_cls=None):
        self.manager = manager
        self.stats_logger_cls = stats_logger_cls or self.stats_logger_cls
        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger(self.logger_name)
        self.raw_logger = logging.getLogger(f"{self.logger.name}.raw")
        self.task_counter = TaskCounter()

    def get_logger_extra(self):
        return {'protocol_name': self.name,
                'peer_ip': self.peer_ip,
                'peer_port': self.peer_port,
                'peer': self.peer,
                'client': self.client,
                'server': self.server,
                'alias': self.alias}

    def get_stats_logger(self, extra):
        return self.stats_logger_cls(extra, self.transport)

    def get_logger(self, extra):
        return ConnectionLogger(self.logger, extra)

    def get_raw_logger(self, extra):
        return ConnectionLogger(self.raw_logger, extra)

    def check_other(self, peer_ip):
        return self.manager.check_sender(peer_ip)

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.info('New %s connection from %s to %s', self.name, self.client, self.server)

    def set_loggers(self):
        extra = self.get_logger_extra()
        self.logger = self.get_logger(extra)
        self.raw_logger = self.raw_logger(extra)
        self.stats_logger = self.get_stats_logger(extra)

    def initialize(self, sock, peer):
        self.peer_ip = peer[0]
        self.peer_port = peer[1]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.own = ':'.join(str(prop) for prop in sock)
        self.sock = sock
        try:
            self.alias = self.check_other(self.peer_ip)
            self.set_loggers()
            return True
        except messagemanagers.MessageFromNotAuthorizedHost:
            self.close_connection()
            return False

    def close_connection(self):
        self.transport.close()

    def connection_lost(self, exc):
        self.logger.manage_error(exc)
        self.logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        self.stats_logger.connection_finished()

    def make_messages(self, encoded, timestamp: datetime):
        try:
            msgs = self.decode_buffer(encoded, timestamp=timestamp)
            self.logger.debug('Buffer contains %s', plural(len(msgs), 'message'))
            for msg in msgs:
                pass
                #self.msg_logger.debug('', extra={'msg_obj': msg})
            return msgs
        except Exception as e:
            self.logger.error(e)
            return None

    def on_data_received(self, buffer, timestamp=None):
        self.logger.debug("Received msg from %s", self.alias)
        self.stats_logger.on_msg_received(buffer)
        self.raw_logger.debug(buffer)
        timestamp = timestamp or datetime.now()
        self.manager.manage_buffer(self.alias, buffer, timestamp)
        msgs = self.make_messages(buffer, timestamp)
        for msg, task in self.manager.manage(msgs):
            response = self.get_response(msg, task)
            self.send(response)

    def send_msg(self, msg_encoded):
        self.logger.debug("Sending message to %s", self.peer)
        self.raw_logger.debug(msg_encoded)
        self.send(msg_encoded)
        self.stats_logger.on_msg_sent(msg_encoded)
        self.logger.debug('Message sent')

    def send_hex(self, hex_msg):
        self.send_msg(binascii.unhexlify(hex_msg))

    def send_msgs(self, msgs):
        for msg in msgs:
            self.send_msg(msg)

    def send_hex_msgs(self, hex_msgs):
        self.send_msgs([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    def encode_and_send_msg(self, msg_decoded):
        msg_encoded = self.encode_msg(msg_decoded)
        self.send_msg(msg_encoded)

    def encode_and_send_msgs(self, decoded_msgs):
        for decoded_msg in decoded_msgs:
            self.encode_and_send_msg(decoded_msg)

    async def play_recording(self, file_path, hosts=(), timing: bool=True):
        self.logger.debug("Playing recording from file %s", file_path)
        for packet in Record.from_file(file_path):
            if (not hosts or packet['host'] in hosts) and not packet['sent_by_server']:
                if timing:
                    await asyncio.sleep(packet['seconds'])
                self.logger.debug('Sending msg with %s bytes', len(packet['data']))
                self.send_msg(packet['data'])
        self.logger.debug("Recording finished")

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def send(self, msg_encoded):
        raise NotImplementedError

    def decode_buffer(self, encoded, timestamp=None):
        return encoded

    def encode_msg(self, msg_obj):
        return msg_obj.encoded

    def get_response(self, msg_obj, task):
        raise NotImplementedError
