import asyncio
import binascii
from collections import ChainMap
from functools import partial
from datetime import datetime

from lib.actions.base import Action
from lib.conf.logging import Logger
from lib.conf.types import ListIPNetworks
from lib.formats.base import BufferObject, MessageObject
from lib.utils import Record, plural
from .exceptions import MessageFromNotAuthorizedHost


class BaseProtocolManager:
    logger_cls = Logger
    logger_name: str = ''
    protocol_cls = None
    connections = []
    name = ''

    configurable = {
        'action': Action,
        'preaction': Action,
        'aliases': dict,
        'timeout': int,
        'dataformat': MessageObject
    }

    @classmethod
    def get_config(cls, cp=None, logger=None, **kwargs):
        from lib import settings
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('Protocol', **cls.configurable)
        config.update(kwargs)
        config['logger'] = logger
        logger.info('Found configuration for %s: %s', cls.name,  config)
        config['action'] = config.pop('action').from_config(cp=cp, logger=logger)
        config['pre_action'] = config.pop('preaction').from_config(cp=cp, logger=logger)
        return config

    @classmethod
    def from_config(cls, **kwargs):
        config = cls.get_config(**kwargs)
        return partial(cls, **config)

    def __init__(self, dataformat, action=None, pre_action=None, aliases=None, allowedsenders=(), logger=None):
        self.data_format = dataformat
        self.action = action
        self.pre_action = pre_action
        self.logger = logger
        if not self.logger:
            self.logger = self.logger_cls(self.logger_name)
        self.protocol_config = {'data_format': dataformat, 'action': action, 'pre_action': pre_action,
                                'aliases':aliases, 'allowed_senders': allowedsenders, 'logger': self.logger,
                                'connection_lost': self.connection_closed}

    @property
    def protocol_kwargs(self):
        return self.protocol_config

    def connection_closed(self, conn):
        self.connections.remove(conn)
        self.logger.debug('Connection closed. There are now %s.', plural(len(self.connections), 'active connection'))

    def get_connection(self):
        conn = self.protocol_cls(**self.protocol_kwargs)
        self.connections.append(conn)
        self.logger.debug('Connection created. There are now %s.', plural(len(self.connections), 'active connection'))
        return conn

    async def close(self):
        self.logger.info('Closing actions')
        await self.pre_action.close()
        await self.action.close()


class BaseNetworkProtocolManager(BaseProtocolManager):
    configurable = ChainMap({'allowedsenders': ListIPNetworks}, BaseProtocolManager.configurable)


class BaseProtocol:
    alias: str = ''
    peer: str = ''
    name: str = ''
    logger = None

    def __init__(self, dataformat, action, pre_action, logger, aliases=None, allowedsenders=(),
                 connection_lost=lambda *args: None):
        self.codec = dataformat.get_codec()
        self.action = action
        self.pre_action = pre_action
        self.aliases = aliases
        self.allowed_senders = allowedsenders
        self.parent_logger = logger
        self.connection_lost = connection_lost
        self.context = {'protocol_name': self.name}

    def get_alias(self, sender: str):
        alias = self.aliases.get(str(sender), sender)
        if alias != sender:
            self.parent_logger.debug('Alias found for %s: %s', sender, alias)
        return alias

    def check_sender(self, other_ip):
        return self.get_alias(other_ip)

    def get_logger(self):
        return self.parent_logger.get_connection_logger(context=self.context)

    def check_other(self, peer_ip):
        return self.check_sender(peer_ip)

    def get_initial_context(self):
        return {}

    def set_logger(self):
        self.context.update(self.get_initial_context())
        self.logger = self.get_logger()
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


class BaseNetworkProtocol(BaseProtocol):
    sock = (None, None)
    own: str = ''
    peer_ip: str = None
    peer_port: int = 0
    transport = None

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
        return {'peer_ip': self.peer_ip,
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
