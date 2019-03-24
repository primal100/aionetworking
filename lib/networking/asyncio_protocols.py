import asyncio
from functools import partial
from datetime import datetime
import binascii
from ipaddress import IPv4Network, IPv6Network, AddressValueError

from lib.counters import TaskCounter
from lib.conf.logging import Logger
from lib.formats.base import BufferObject
from lib.utils import Record, plural
from .exceptions import MessageFromNotAuthorizedHost
from lib.conf.logging import ConnectionLogger


class BaseMessageManager:
    alias: str = ''
    peer: str = ''
    logger_cls = ConnectionLogger
    name: str = ''
    parent_logger_name: str = ''
    logger: None
    context: dict = {}

    configurable = {
        'action': tuple,
        'preaction': tuple,
        'aliases': dict,
        'timeout': int,
        'dataformat': str
    }

    @classmethod
    def get_config(cls, cp=None, logger=None, **kwargs):
        from lib import settings, definitions
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Protocol', **cls.configurable)
        config.update(kwargs)
        logger.info('Found configuration for %s: %s', cls.name,  config)
        config['action'] = definitions.ACTIONS[config.pop('action')].from_config(cp=cp, logger=logger)
        config['pre_action'] = definitions.ACTIONS[config.pop('preaction')].from_config(cp=cp, logger=logger)
        config['dataformat'] = definitions.DATA_FORMATS[config.pop('dataaction')]
        config['logger'] = logger
        config['connection_logger_cls'] = cls.logger_cls.with_config(logger, cp=cp)
        return config

    @classmethod
    def with_config(cls, cp=None, **kwargs):
        config = cls.get_config(cp=cp, **kwargs)
        return partial(cls, **config)

    def __init__(self, dataformat, action=None, pre_action=None, aliases=None, allowedsenders=(),
                 logger=None, connection_logger_cls=None):
        self.codec = dataformat.get_codec()
        self.action = action
        self.pre_action = pre_action
        self.aliases = aliases
        self.allowed_senders = allowedsenders
        self.parent_logger = logger or Logger(self.parent_logger_name)
        self.connection_logger_cls = connection_logger_cls or self.connection_logger_cls
        self.task_counter = TaskCounter()

    def get_alias(self, sender: str):
        alias = self.aliases.get(str(sender), sender)
        if alias != sender:
            self.parent_logger.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        return self.get_alias(other_ip)

    def get_logger(self, extra):
        return self.parent_logger.get_child('connection', cls=self.logger_cls, context=extra)

    def check_other(self, peer_ip):
        return self.check_sender(peer_ip)

    def get_initial_context(self):
        return {'protocol_name': self.name}

    def set_logger(self):
        self.context = self.get_initial_context()
        self.logger = self.get_logger(self.context)
        self.codec.set_logger(self.logger)

    def make_messages(self, encoded, timestamp: datetime):
        msgs = self.decode_buffer(encoded, timestamp=timestamp)
        self.logger.debug('Buffer contains %s', plural(len(msgs), 'message'))
        self.logger.log_decoded_msgs(msgs)
        return msgs

    def manage_buffer(self, buffer, timestamp):
        self.logger.on_buffer_received(buffer)
        if self.pre_action:
            buffer = BufferObject(buffer, timestamp=timestamp, logger=self.logger)
            self.pre_action.do_one(buffer)

    def decode_buffer(self, buffer, timestamp=None):
        return self.codec.from_buffer(buffer, timestamp=timestamp, context=self.context)

    def send_msg(self, msg_encoded):
        self.logger.on_sending_encoded_msg(msg_encoded)
        self.send(msg_encoded)
        self.logger.on_msg_sent(msg_encoded)

    def send_hex(self, hex_msg):
        self.send_msg(binascii.unhexlify(hex_msg))

    def send_msgs(self, msgs):
        for msg in msgs:
            self.send_msg(msg)

    def send_hex_msgs(self, hex_msgs):
        self.send_msgs([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    def encode_msg(self, decoded):
        return self.codec.encode(decoded, context=self.context)

    def encode_and_send_msg(self, msg_decoded):
        self.logger.on_sending_decoded_msg(msg_decoded)
        msg_obj = self.encode_msg(msg_decoded)
        self.send_msg(msg_obj.encoded)

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

    def on_data_received(self, buffer, timestamp=None):
        raise NotImplementedError

    def send(self, msg_encoded):
        raise NotImplementedError


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

    def on_data_received(self, buffer, timestamp=None):
        raise NotImplementedError

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.new_connection()

    def close_connection(self):
        self.transport.close()

    def connection_lost(self, exc):
        self.logger.connection_finished(exc)

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
            self.set_logger()
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
