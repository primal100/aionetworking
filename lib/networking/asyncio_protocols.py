import asyncio
from abc import ABC, abstractmethod
import binascii
from datetime import datetime
from dataclasses import dataclass, field, replace

from lib.actions.base import Action
from lib.conf.logging import Logger
from lib.formats.base import BufferObject, BaseMessageObject
from lib.utils import Record
from lib.utils_logging import p
from lib.conf.pydantic_future import IPvAnyNetwork
from .exceptions import MessageFromNotAuthorizedHost

from typing import Type, ClassVar, Tuple


@dataclass
class BaseProtocol(ABC):
    name = ''

    logger: Logger = None
    action: Action = None
    preaction: Action = None
    aliases: dict = field(default_factory=dict)
    timeout: int = 0
    dataformat: Type[BaseMessageObject] = None

    def __post_init__(self):
        self.codec = self.dataformat.get_codec()
        self.parent_logger = self.logger
        self._context = {'protocol_name': self.name}

    def __call__(self):
        return replace(self)

    async def close(self):
        self.logger.info('Closing actions')
        await self.preaction.close()
        await self.action.close()

    @property
    def context(self):
        return self._context

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

    @property
    def connection_context(self):
        return {}

    def set_logger(self):
        self._context.update(self.connection_context)
        self.logger = self.get_logger()
        self.codec.set_logger(self.logger)

    def make_messages(self, encoded, timestamp: datetime):
        msgs = self.decode_buffer(encoded, timestamp=timestamp)
        self.logger.debug('Buffer contains %s', p.no('message', msgs))
        self.logger.log_decoded_msgs(msgs)
        return msgs

    def manage_buffer(self, buffer, timestamp):
        self.logger.on_buffer_received(buffer)
        if self.preaction:
            buffer = BufferObject(buffer, timestamp=timestamp, logger=self.logger)
            self.preaction.do_one(buffer)

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
                self.logger.debug('Sending msg with %s', p.no('byte', packet['data']))
                self.send_msg(packet['data'])
        self.logger.debug("Recording finished")

    @abstractmethod
    def on_data_received(self, buffer, timestamp=None): ...

    @abstractmethod
    def send(self, msg_encoded): ...


@dataclass
class BaseNetworkProtocol(ABC, BaseProtocol):
    sock = (None, None)
    own: ''
    alias = ''
    peer = None
    peer_ip = None
    peer_port = 0
    transport = None

    _connections: ClassVar = {}
    allowed_senders: Tuple[IPvAnyNetwork] = field(default_factory=())

    @property
    @abstractmethod
    def client(self): ...

    @property
    @abstractmethod
    def server(self): ...

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.initialize(sock, peer)
        if connection_ok:
            self.logger.new_connection()
            self._connections[self.peer] = self
            self.logger.debug('Connection opened. There %s now %s.', p.plural_verb('is', p.num(len(self._connections))),
                              p.no('active connection'))

    def close_connection(self):
        pass

    def connection_lost(self, exc):
        self.logger.connection_finished(exc)
        self.close_connection()
        self._connections.pop(self.peer, None)

    @property
    def connection_context(self):
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
        msg = f"Received message from unauthorized host {sender}"
        self.logger.error(msg)
        raise MessageFromNotAuthorizedHost(msg)

    def sender_valid(self, other_ip):
        if self.allowed_networks:
            return any(n.supernet_of(other_ip) for n in self.allowed_networks)
        return True

    def check_sender(self, other_ip):
        if self.sender_valid(other_ip):
            return super(BaseNetworkProtocol,self).check_sender(other_ip)
        self.raise_message_from_not_authorized_host(other_ip)
