import asyncio
from datetime import datetime
from functools import partial
from .exceptions import MethodNotFoundError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.networking.asyncio_protocols import BaseMessageManager as _BaseProtocol
    from lib.receivers.asyncio_servers import BaseAsyncioServer as _BaseReceiver
else:
    _Base = object
    _BaseReceiver = object


class TCP(_BaseReceiver):
    ssl_section_name:str = None
    ssl_cls = None

    #Dataclass fields
    ssl_handshake_timeout: int

    @classmethod
    def from_config(cls, *args, logger=None, config=None, cp=None, **kwargs):
        ssl = cls.ssl_cls.get_context('SSLServer', logger=logger, cp=cp)
        return super().from_config(*args, cp=cp, config=config, ssl=ssl, **kwargs)

    def __init__(self, *args, ssl: bool = None, sslhandshaketimeout: int=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl = ssl
        self.ssl_handshake_timeout = sslhandshaketimeout


class ClientProtocolMixin(_BaseProtocol):
    logger_name = 'sender'
    futures = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notification_queue = asyncio.Queue()

    def send(self, msg_encoded):
        raise NotImplementedError

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
        return await self.notification_queue.get()

    def get_notification(self):
        return self.notification_queue.get_nowait()

    async def wait_notifications(self):
        for item in await self.notification_queue.get():
            yield item

    def get_all_notifications(self):
        for i in range(0, self.notification_queue.qsize()):
            yield self.notification_queue.get_nowait()

    async def send_and_wait(self, request_id, encoded):
        fut = asyncio.Future()
        self.futures[request_id] = fut
        self.send_msg(encoded)
        await fut
        del self.futures[request_id]
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
            fut = self.futures.get(msg.request_id, None)
            if fut:
                fut.set_result(msg)
            else:
                self.notification_queue.put_nowait(msg)


class BaseServerProtocolMixin(_BaseProtocol):
    logger_name = 'receiver'

    def send(self, msg_encoded):
        raise NotImplementedError

    @property
    def client(self) -> str:
        if self.alias:
            return '%s(%s)' % (self.alias, self.peer)
        return self.peer

    @property
    def server(self) -> str:
        return self.sock


class OneWayServerProtocolMixin(BaseServerProtocolMixin):

    def send(self, msg_encoded):
        raise NotImplementedError

    def on_data_received(self, buffer, timestamp=None):
        timestamp = timestamp or datetime.now()
        self.manage_buffer(self.alias, buffer, timestamp)
        msgs = self.make_messages(buffer, timestamp)
        self.action.do_many(msgs)


class ServerProtocolMixin(_BaseProtocol):

    def send(self, msg_encoded):
        raise NotImplementedError

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


