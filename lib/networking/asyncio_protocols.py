import asyncio
from functools import partial
from datetime import datetime
import binascii
import time
import logging
from ipaddress import IPv4Network, IPv6Network, AddressValueError

from lib.counters import TaskCounter
from lib.protocols.base import BufferObject
from lib.utils import Record, plural
from .exceptions import MessageFromNotAuthorizedHost
from .logging import ConnectionLogger, StatsLogger


class BaseMessageManager:
    alias: str = ''
    peer: str = ''
    stats_cls = StatsLogger
    name: str = ''
    logger_name: str = ''
    logger: None
    stats_logger = None
    context: dict = {}

    configurable = {
        'action': tuple,
        'preaction': tuple,
        'aliases': dict,
        'timeout': int
    }

    @classmethod
    def get_config(cls, logger, cp=None, **kwargs):
        from lib import settings, definitions
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('MessageManager', **cls.configurable)
        config.update(kwargs)
        logger.info('Found configuration for %s: %s', cls.name,  config)
        config['action'] = definitions.ACTIONS[config.pop('action')].from_config(cp=cp)
        config['pre_action'] = definitions.ACTIONS[config.pop('preaction')].from_config(cp=cp)
        config['logger'] = logging.getLogger(f'{logger.name}.connection')
        config['stats_logger_cls'] = cls.stats_cls.with_config(logger, cp=cp)
        return config

    @classmethod
    def with_config(cls, logger, cp=None, **kwargs):
        config = cls.get_config(logger, cp=cp, **kwargs)
        return partial(cls, **config)

    def __getattr__(self, item):
        if item in getattr(self.action, 'methods', ()) or item in getattr(self.action, 'notification_methods', ()):
            return partial(getattr(self.action, item), self)

    def __init__(self, action=None, pre_action=None, aliases=None, allowedsenders=(),
                 timeout=5, logger=None, stats_logger_cls=None):
        self.action = action
        self.pre_action = pre_action
        self.aliases = aliases
        self.allowed_senders = allowedsenders
        self.stats_logger_cls = stats_logger_cls or self.stats_logger_cls
        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger(self.logger_name)
        self.raw_logger = logging.getLogger(f"{self.logger.name}.raw")
        self.task_counter = TaskCounter()

    def get_alias(self, sender: str):
        alias = self.aliases.get(str(sender), sender)
        if alias != sender:
            self.logger.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        return self.get_alias(other_ip)

    def get_stats_logger(self, extra):
        return self.stats_logger_cls(extra)

    def get_logger(self, extra):
        return ConnectionLogger(self.logger, extra)

    def get_raw_logger(self, extra):
        return ConnectionLogger(self.raw_logger, extra)

    def check_other(self, peer_ip):
        return self.check_sender(peer_ip)

    def get_initial_context(self):
        return {'protocol_name': self.name}

    def set_loggers(self):
        self.context = self.get_initial_context()
        self.logger = self.get_logger(self.context)
        self.raw_logger = self.raw_logger(self.context)
        self.stats_logger = self.get_stats_logger(self.context)

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

    def manage_buffer(self, sender, buffer, timestamp):
        if self.pre_action:
            buffer = BufferObject(sender, buffer, timestamp=timestamp, logger=self.logger)
            self.pre_action.do_one(buffer)

    def on_data_received(self, buffer, timestamp=None):
        self.logger.debug("Received msg from %s", self.alias)
        self.stats_logger.on_msg_received(buffer)
        self.raw_logger.debug(buffer)
        timestamp = timestamp or datetime.now()
        self.manage_buffer(self.alias, buffer, timestamp)
        msgs = self.make_messages(buffer, timestamp)
        for msg_obj, task in self.action.do_many(msgs):
            if task:
                task.add_done_callback(partial(self.on_task_complete, msg_obj))

    def on_task_complete(self, msg_obj, future):
        response = self.process_result(msg_obj, future)
        if response:
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

    def send(self, msg_encoded):
        raise NotImplementedError

    def encode_msg(self, decoded):
        msg_obj = self.codec.encode(decoded)
        return msg_obj.encoded

    def encode_exception(self, msg_obj, exception):...

    def process_result(self, msg_obj, task):
        result, exception = task.result(), task.exception()
        if result:
            return self.encode_msg(result)
        if exception():
            self.logger.error(exception)
            return self.encode_exception(msg_obj, exception)


class BaseNetworkProtocol(BaseMessageManager):
    sock = (None, None)
    own: str = ''
    peer_ip: str = None
    peer_port: int = 0
    transport = None
    configurable = BaseMessageManager.configurable.copy()
    configurable.update({'allowednetworks': tuple})

    @staticmethod
    def get_network(network):
        try:
            return IPv4Network(network)
        except AddressValueError:
            return IPv6Network(network)

    @classmethod
    def from_config(cls, *args, **kwargs):
        config = super().get_config(*args, **kwargs)
        allowed_networks = config.pop('allowednetworks')
        networks = []
        for network in allowed_networks:
            try:
                networks.append(cls.get_network(network))
            except AddressValueError:
                config['logger'].error("%s is not a valid IP network", network)
        config['allowednetworks'] = networks
        return cls(*args, **config)

    def __init__(self, *args, allowednetworks=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_networks = allowednetworks

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def send(self, msg_encoded):
        raise NotImplementedError

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.info('New %s connection from %s to %s', self.name, self.client, self.server)

    def close_connection(self):
        self.transport.close()

    def connection_lost(self, exc):
        self.stats_logger.set_closing()
        self.logger.manage_error(exc)
        self.logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        self.stats_logger.connection_finished()

    def get_initial_context(self):
        return {'protocol_name': self.name,
                'peer_ip': self.peer_ip,
                'peer_port': self.peer_port,
                'peer': self.peer,
                'client': self.client,
                'server': self.server,
                'alias': self.alias}

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
        except MessageFromNotAuthorizedHost:
            self.close_connection()
            return False

    def raise_message_from_not_authorized_host(self, sender):
        msg = f"Received message from unauthorized host {sender}. Authorized hosts are: {self.allowed_senders}. Allowed networks are: {self.allowed_networks}"
        self.logger.error(msg)
        raise MessageFromNotAuthorizedHost(msg)

    def sender_valid(self, other_ip):
        if self.allowed_networks:
            network = self.get_network(other_ip)
            if all(not n.supernet_of(network) for n in self.allowed_networks):
                return False
        return True

    def check_sender(self, other_ip):
        if self.sender_valid(other_ip):
            return super(BaseNetworkProtocol,self).check_sender(other_ip)
        self.raise_message_from_not_authorized_host(other_ip)

