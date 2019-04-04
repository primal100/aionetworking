from abc import ABC
import asyncio
from datetime import datetime
from dataclasses import field
from functools import partial

from pydantic.dataclasses import dataclass

from .exceptions import MethodNotFoundError
from lib.conf.logging import Logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.networking.asyncio_protocols import BaseNetworkProtocol as _BaseProtocol
else:
    _Base = object
    _BaseReceiver = object


@dataclass
class ClientProtocolMixin(ABC, _BaseProtocol):
    logger: Logger = 'sender'
    _futures: dict = field(default_factory=dict, init=False, repr=False, hash=False, compare=False)
    _notification_queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False, compare=False)

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer

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


@dataclass
class BaseServerProtocolMixin(ABC, _BaseProtocol):
    logger: Logger = 'sender'

    @property
    def client(self) -> str:
        if self.alias:
            return '%s(%s)' % (self.alias, self.peer)
        return self.peer

    @property
    def server(self) -> str:
        return self.sock


@dataclass
class OneWayServerProtocolMixin(BaseServerProtocolMixin):

    def send(self, msg_encoded):
        raise NotImplementedError('Not able to send messages with one-way server')

    def on_data_received(self, buffer, timestamp=None):
        timestamp = timestamp or datetime.now()
        self.manage_buffer(self.alias, buffer, timestamp)
        msgs = self.make_messages(buffer, timestamp)
        self.action.do_many(msgs)


@dataclass
class ServerProtocolMixin(BaseServerProtocolMixin):

    def on_task_complete(self, msg_obj, future):
        response = self.process_result(msg_obj, future)
        if response:
            self.send(response)

    def on_data_received(self, buffer, timestamp=None):
        timestamp = timestamp or datetime.now()
        self.manage_buffer(buffer, timestamp)
        try:
            msgs = self.make_messages(buffer, timestamp)
        except Exception as e:
            self.logger.error(e)
            response = self.action.response_on_decode_error(buffer, e)
            if response:
                self.encode_and_send_msg(response)
        else:
            for msg_obj, task in self.action.do_many(msgs):
                if task:
                    task.add_done_callback(partial(self.on_task_complete, msg_obj))

    def encode_exception(self, msg_obj, exc):
        return self.action.response_on_exception(msg_obj, exc)

    def process_result(self, msg_obj, task):
        result, exception = task.result(), task.exception()
        if result:
            return self.encode_msg(result)
        if exception():
            self.logger.error(exception)
            return self.encode_exception(msg_obj, exception)


