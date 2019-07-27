from abc import abstractmethod
import asyncio
import binascii
import contextvars
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial

from .exceptions import MethodNotFoundError
from lib.actions.protocols import BaseActionProtocol, OneWaySequentialAction, ParallelAction
from lib.conf.logging import ConnectionLogger
from lib.formats.base import MessageObjectType, BaseCodec, BaseMessageObject, BufferObject
from lib.requesters.base import BaseRequester
from lib.utils import Record
from lib.utils_logging import p
from lib.wrappers.schedulers import TaskScheduler

from .protocols import AdaptorProtocol

from pathlib import Path
from typing import Any, AnyStr, AsyncGenerator, Callable, Generator, Iterator, MutableMapping, Sequence, Type, Optional, Union
from typing_extensions import Protocol


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


def not_implemented_callable(*args, **kwargs) -> None:
    raise NotImplementedError


@dataclass
class BaseAdaptorProtocol(AdaptorProtocol, Protocol):
    dataformat: Type[BaseMessageObject]
    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger = None
    context: MutableMapping = field(default_factory=dict)
    preaction: OneWaySequentialAction = None
    send: Callable = not_implemented_callable

    def __post_init__(self) -> None:
        self.codec: BaseCodec = self.dataformat.get_codec(logger=self.logger, context=self.context)
        self.logger.new_connection()

    def send_data(self, msg_encoded: AnyStr) -> None:
        self.logger.on_sending_encoded_msg(msg_encoded)
        self.send(msg_encoded)
        self.logger.on_msg_sent(msg_encoded)

    def send_hex(self, hex_msg: AnyStr) -> None:
        self.send_data(binascii.unhexlify(hex_msg))

    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None:
        for msg in hex_msgs:
            self.send(binascii.unhexlify(msg))

    def encode_msg(self, decoded: Any) -> MessageObjectType:
        return self.codec.encode(decoded)

    def encode_and_send_msg(self, msg_decoded: Any) -> None:
        self.logger.on_sending_decoded_msg(msg_decoded)
        msg_obj = self.encode_msg(msg_decoded)
        self.send_data(msg_obj.encoded)

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None:
        for decoded_msg in decoded_msgs:
            self.encode_and_send_msg(decoded_msg)

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
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...

    async def close(self, exc: Optional[BaseException], timeout: Union[int, float]) -> None:
        self.logger.connection_finished(exc)
        if self.preaction:
            await self.preaction.close()
        await self._scheduler.close(timeout=timeout)


@dataclass
class SenderAdaptor(BaseAdaptorProtocol):
    is_receiver = False
    requester: BaseRequester = None

    _notification_queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False,
                                               compare=False)

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


@dataclass
class BaseReceiverAdaptor(BaseAdaptorProtocol, Protocol):
    is_receiver = True
    action: BaseActionProtocol = None

    async def close(self, exc: Optional[BaseException], timeout: Union[int, float] = None) -> None:
        await super().close(exc, timeout=timeout)
        if self.action:
            await self.action.close()


@dataclass
class OneWayReceiverAdaptor(BaseReceiverAdaptor):
    action: OneWaySequentialAction = None

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        self.action.do_many(msgs)


@dataclass
class ReceiverAdaptor(OneWayReceiverAdaptor):
    action: ParallelAction = None

    def on_exception(self, msg_obj: MessageObjectType, exc: BaseException) -> MessageObjectType:
        return self.action.response_on_exception(msg_obj, exc)

    def process_result(self, future: asyncio.Future) -> MessageObjectType:
        result, exception = future.result(), future.exception()
        if result:
            return result
        if exception:
            self.logger.error(exception)
            return self.on_exception(msg_obj_cv.get(), exception)

    def on_task_complete(self, future: asyncio.Future) -> None:
        try:
            response = self.process_result(future)
            if response:
                self.encode_and_send_msg(response)
        finally:
            self._scheduler.task_done(future)

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        try:
            for msg in msgs:
                msg_obj_cv.set(msg)
                self._scheduler.create_task(self.action.asnyc_do_one(msg), callback=self.on_task_complete)
        except Exception as e:
            self.logger.error(e)
            response = self.action.response_on_decode_error(buffer, e)
            if response:
                self.encode_and_send_msg(response)
