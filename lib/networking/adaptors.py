import asyncio
import contextvars
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial

from .exceptions import MethodNotFoundError
from lib.actions.protocols import OneWaySequentialAction, ParallelAction
from lib.conf.logging import Logger
from lib.formats.base import MessageObjectType, BaseCodec, BaseMessageObject
from lib.requesters.base import BaseRequester
from lib.utils import Record
from lib.wrappers.schedulers import TaskScheduler

from .protocols import AdaptorProtocol, ProtocolType
from typing import Any, AnyStr, AsyncGenerator, Callable, Generator, Iterator, MutableMapping, Sequence, Type, Union
from typing_extensions import Protocol


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


def not_implemented_callable(*args, **kwargs) -> None:
    raise NotImplementedError


@dataclass
class BaseAdaptor( Protocol):
    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger = None
    context: MutableMapping = field(default_factory=dict)
    dataformat: Type[BaseMessageObject] = None
    codec: BaseCodec = None
    preaction: OneWaySequentialAction = None
    parent_logger: Logger = Logger('receiver')
    parent: int = None
    timeout: Union[int, float] = 5
    send: Callable = not_implemented_callable

    async def close(self) -> None:
        await self._scheduler.close(timeout=self.timeout)


@dataclass
class ClientAdaptor(BaseAdaptor):
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
class OneWayServerAdaptor(BaseAdaptor):
    is_receiver = True
    action: OneWaySequentialAction = None

    async def close(self) -> None:
        self.logger.info('Closing Adaptor')
        if self.preaction:
            await self.preaction.close()
        if self.action:
            await self.action.close()

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None:
        self.action.do_many(msgs)


@dataclass
class ServerAdaptor(OneWayServerAdaptor):
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
        response = self.process_result(future)
        if response:
            self.encode_and_send_msg(response)
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
