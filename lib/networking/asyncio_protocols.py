from abc import ABC, abstractmethod
import asyncio
import binascii
from datetime import datetime
from dataclasses import field, replace
from functools import partial

from .exceptions import MethodNotFoundError
from lib.actions.base import BaseAction
from lib.conf.logging import Logger
from lib.formats.base import BaseMessageObject, BufferObject
from lib.requesters.base import BaseRequester
from lib.types import Type
from lib.utils import Record
from lib.utils_logging import p

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pydantic.dataclasses import dataclass
else:
    from dataclasses import dataclass


@dataclass
class BaseProtocol(ABC):
    name = ''
    codec = None

    logger: Logger = None
    aliases: dict = field(default_factory=dict)
    timeout: int = 0
    dataformat: Type[BaseMessageObject] = None

    def __post_init__(self):
        self.codec = self.dataformat.get_codec(logger=self.logger)
        self.parent_logger = self.logger
        self._context = {'protocol_name': self.name}

    def __call__(self):
        return replace(self)

    async def close(self):
        pass

    @property
    def context(self):
        return self._context

    def get_alias(self, peer: str):
        alias = self.aliases.get(str(peer), peer)
        if alias != peer:
            self.parent_logger.debug('Alias found for %s: %s', peer, alias)
        return alias

    def get_logger(self):
        return self.parent_logger.get_connection_logger(context=self.context)

    def check_other(self, peer: str):
        return self.get_alias(peer)

    @property
    def connection_context(self):
        return {}

    def configure_context(self):
        self._context.update(self.connection_context)
        self.logger = self.get_logger()
        self.codec.set_context(self.context, logger=self.logger)

    def make_messages(self, encoded, timestamp: datetime):
        msgs = self.decode_buffer(encoded, timestamp=timestamp)
        self.logger.debug('Buffer contains %s', p.no('message', msgs))
        self.logger.log_decoded_msgs(msgs)
        return msgs

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
class BaseReceiverProtocol(ABC, BaseProtocol):
    action: BaseAction = None
    preaction: BaseAction = None

    async def close(self):
        self.logger.info('Closing actions')
        await self.preaction.close()
        await self.action.close()

    def manage_buffer(self, buffer, timestamp):
        self.logger.on_buffer_received(buffer)
        if self.preaction:
            buffer = BufferObject(buffer, timestamp=timestamp, logger=self.logger)
            self.preaction.do_one(buffer)

    def on_data_received(self, buffer, timestamp=None):
        timestamp = timestamp or datetime.now()
        self.manage_buffer(buffer, timestamp)
        msgs = self.make_messages(buffer, timestamp)
        self.action.do_many(msgs)

    def send(self, msg_encoded):
        raise NotImplementedError(f"Not able to send messages with {self.name}")


@dataclass
class BaseSenderProtocol(ABC, BaseProtocol):
    requestor: BaseRequester = None
    logger: Logger = 'sender'

    _futures: dict = field(default_factory=dict, init=False, repr=False, hash=False, compare=False)
    _notification_queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False, compare=False)

    def __getattr__(self, item):
        if item in getattr(self.action, 'methods', ()):
            return partial(self._send_and_wait, getattr(self.action, item))
        if item in getattr(self.action, 'notification_methods', ()):
            return partial(self._send_request, getattr(self.action, item))
        raise MethodNotFoundError(f'{item} method was not found')

    def _send_request(self, method, *args, **kwargs):
        msg_decoded = method(*args, **kwargs)
        self.encode_and_send_msg(msg_decoded)

    async def wait_notification(self):
        return await self._notification_queue.get()

    def get_notification(self):
        return self._notification_queue.get_nowait()

    async def wait_notifications(self):
        for item in await self._notification_queue.get():
            yield item

    def get_all_notifications(self):
        for i in range(0, self._notification_queue.qsize()):
            yield self._notification_queue.get_nowait()

    async def send_and_wait(self, request_id, encoded):
        fut = asyncio.Future()
        self._futures[request_id] = fut
        self.send_msg(encoded)
        await fut
        del self._futures[request_id]
        return fut

    async def send_msg_and_wait(self, msg_obj):
        return await self.send_and_wait(msg_obj.request_id, msg_obj.encoded)

    async def encode_send_wait(self, decoded):
        msg_obj = self.encode_msg(decoded)
        return await self.send_msg_and_wait(msg_obj)

    async def _send_and_wait(self, method, *args, **kwargs):
        msg_decoded = method(*args, **kwargs)
        return await self.encode_send_wait(msg_decoded)

    def on_data_received(self, buffer, timestamp=None):
        timestamp = timestamp or datetime.now()
        msgs = self.make_messages(buffer, timestamp)
        for msg in msgs:
            fut = self._futures.get(msg.request_id, None)
            if fut:
                fut.set_result(msg)
            else:
                self._notification_queue.put_nowait(msg)
