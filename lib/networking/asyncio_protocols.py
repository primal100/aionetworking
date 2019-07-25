from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
import binascii
import contextvars
from datetime import datetime
from dataclasses import InitVar, dataclass, field, replace
from functools import partial
from pathlib import Path

from .exceptions import MethodNotFoundError
from lib.formats.base import BufferObject
from lib.types import Type
from lib.utils import Record
from lib.utils_logging import p
from lib.wrappers.schedulers import TaskScheduler

from lib.actions.base import BaseAction
from lib.formats.base import BaseCodec, MessageObjectType
from lib.conf.logging import Logger, ConnectionLogger
from lib.requesters.base import BaseRequester

from .protocols import DataProtocol, ProtocolType

from typing import Any, AnyStr, Callable, Iterator, MutableMapping, Sequence, AsyncGenerator, Generator, Union


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


def not_implemented_callable(*args, **kwargs) -> None:
    raise NotImplementedError


@dataclass
class BaseProtocol(DataProtocol):
    name = ''
    is_receiver = True
    connection_logger_cls = ConnectionLogger
    initialize_adaptor_immediately = True

    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger = field(default=None, init=False, hash=False, compare=False, repr=False)
    context: MutableMapping = field(default_factory=dict)
    dataformat: Type[MessageObjectType] = None
    codec: BaseCodec = None
    preaction: BaseAction = None
    parent_logger: Logger = Logger('receiver')
    parent: int = None
    timeout: Union[int, float] = 5

    def __post_init__(self) -> None:
        if self.dataformat and not self.codec:
            self.codec: BaseCodec = self.dataformat.get_codec(logger=self.parent_logger)
        self.context['protocol_name'] = self.name
        if self.initialize_adaptor_immediately:
            self._configure_context()
            self._configure_adaptor()

    @abstractmethod
    def _configure_adaptor(self):
        raise NotImplementedError

    def __call__(self, **kwargs):
        return self._clone(**kwargs)

    def _clone(self: ProtocolType, **kwargs) -> ProtocolType:
        return replace(self, parent=id(self), **kwargs)

    def _configure_context(self) -> None:
        self.set_logger()
        self.codec.set_context(self.context, logger=self.logger)

    def is_owner(self, connection: ProtocolType) -> bool:
        return connection.parent == id(self)

    async def close(self) -> None:
        await self.adaptor.close()
        await self._scheduler.close(timeout=self.timeout)

    def set_logger(self) -> None:
        self.logger = self.parent_logger.get_connection_logger(is_receiver=self.is_receiver, context=self.context)

    def send_data(self, msg_encoded: AnyStr) -> None:
        self.logger.on_sending_encoded_msg(msg_encoded)
        self.send(msg_encoded)
        self.logger.on_msg_sent(msg_encoded)

    def send_hex(self, hex_msg: AnyStr) -> None:
        self.send_data(binascii.unhexlify(hex_msg))

    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None:
        self.send_many([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    def encode_msg(self, decoded: Any) -> MessageObjectType:
        return self.codec.encode(decoded)

    def encode_and_send_msg(self, msg_decoded: Any) -> None:
        self.logger.on_sending_decoded_msg(msg_decoded)
        msg_obj = self.encode_msg(msg_decoded)
        self.send_data(msg_obj.encoded)

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None:
        for decoded_msg in decoded_msgs:
            self.encode_and_send_msg(decoded_msg)

    def send_many(self, data_list: Sequence[AnyStr]):
        for data in data_list:
            self.send(data)

    def _manage_buffer(self, buffer: AnyStr, timestamp: datetime = None) -> None:
        self.logger.on_buffer_received(buffer)
        if self.preaction:
            buffer = BufferObject(buffer, received_timestamp=timestamp, logger=self.logger, context=self.context)
            self.preaction.do_many([buffer])

    def on_data_received(self, buffer: AnyStr, timestamp: datetime = None) -> None:
        timestamp = timestamp or datetime.now()
        self._manage_buffer(buffer, timestamp)
        msgs = self.codec.decode_buffer(buffer, received_timestamp=timestamp)
        self.process_msgs(msgs, buffer)

    @abstractmethod
    def process_msgs(self, msgs: Sequence[MessageObjectType], buffer: AnyStr) -> None:
        raise NotImplementedError

    @abstractmethod
    def send(self, data: AnyStr):
        raise NotImplementedError


@dataclass
class BaseAdaptor(ABC):
    is_receiver = True
    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger
    task_callback: Callable
    preaction: BaseAction = None

    def close(self):
        await self._scheduler.close()

    def task_callback(self, fut: asyncio.Future):
        self.task_callback(fut)
        self._scheduler.task_done(fut)


@dataclass
class BaseOneWayReceiverAdaptor(BaseAdaptor):
    is_receiver = True
    action: BaseAction = None

    async def close(self) -> None:
        self.logger.info('Closing Adaptor')
        super().close()
        if self.preaction:
            await self.preaction.close()
        if self.action:
            await self.action.close()

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        self.action.do_many(msgs)


@dataclass
class BaseReceiverAdaptor(BaseOneWayReceiverAdaptor):

    def encode_exception(self, msg_obj: MessageObjectType, exc: BaseException) -> MessageObjectType:
        return self.action.response_on_exception(msg_obj, exc)

    def process_result(self, future: asyncio.Future) -> MessageObjectType:
        result, exception = future.result(), future.exception()
        if result:
            return self.encode_msg(result)
        if exception:
            self.logger.error(exception)
            return self.encode_exception(msg_obj_cv.get(), exception)

    def on_task_complete(self, future: asyncio.Future) -> None:
        response = self.process_result(future)
        if response:
            self.send(response)
        self._scheduler.task_done(future)

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        try:
            for msg in msgs:
                msg_obj_cv.set(msg)
                self._scheduler.create_task(self.action.do_one(msg), callback=self.on_task_complete)
        except Exception as e:
            self.logger.error(e)
            response = self.action.response_on_decode_error(buffer, e)
            if response:
                self.encode_and_send_msg(response)


@dataclass
class BaseSenderAdaptor(ABC):
    is_receiver = False
    requester: BaseRequester = None

    _notification_queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False, compare=False)

    def __getattr__(self, item):
        if item in getattr(self.requester, 'methods', ()):
            return partial(self._run_method_and_wait, getattr(self.requester, item))
        if item in getattr(self.requester, 'notification_methods', ()):
            return partial(self._run_method, getattr(self.requester, item))
        raise MethodNotFoundError(f'{item} method was not found')

    async def wait_notification(self) -> MessageObjectType:
        return await self._notification_queue.get()

    def get_notification(self) -> MessageObjectType:
        return self._notification_queue.get_nowait()

    async def wait_notifications(self) -> AsyncGenerator[MessageObjectType, None]:
        for item in await self._notification_queue.get():
            yield item

    def all_notifications(self) -> Generator[MessageObjectType, None, None]:
        for i in range(0, self._notification_queue.qsize()):
            yield self._notification_queue.get_nowait()

    async def send_data_and_wait(self, request_id: Any, encoded: AnyStr) -> asyncio.Future:
        fut = self._scheduler.create_future(request_id)
        self.send_data(encoded)
        await fut
        self._scheduler.future_done(request_id)
        return fut

    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future:
        return await self.send_data_and_wait(msg_obj.request_id, msg_obj.encoded)

    async def encode_send_wait(self, decoded: Any) -> asyncio.Future:
        msg_obj = self.encode_msg(decoded)
        return await self.send_msg_and_wait(msg_obj)

    def _run_method(self, method: Callable, *args, **kwargs) -> None:
        msg_decoded = method(*args, **kwargs)
        self.encode_and_send_msg(msg_decoded)

    async def _run_method_and_wait(self, method: Callable, *args, **kwargs) -> asyncio.Future:
        msg_decoded = method(*args, **kwargs)
        return await self.encode_send_wait(msg_decoded)

    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None:
        self.logger.debug("Playing recording from file %s", file_path)
        for packet in Record.from_file(file_path):
            if (not hosts or packet['host'] in hosts) and not packet['sent_by_server']:
                if timing:
                    await asyncio.sleep(packet['seconds'])
                self.logger.debug('Sending msg with %s', p.no('byte', packet['data']))
                self.send_data(packet['data'])
        self.logger.debug("Recording finished")

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        for msg in msgs:
            if msg.request_id:
                self._scheduler.set_result(msg.requst_id, msg)
            else:
                self._notification_queue.put_nowait(msg)
