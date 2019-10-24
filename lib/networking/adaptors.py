from abc import abstractmethod
import asyncio
import contextvars
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial

from .exceptions import MethodNotFoundError, RemoteConnectionClosedError
from lib.actions.protocols import ActionProtocol
from lib.compatibility import Protocol
from lib.conf.logging import connection_logger_cv, ConnectionLogger
from lib.conf.context import context_cv
from lib.formats.base import MessageObjectType, BaseCodec, BaseMessageObject
from lib.formats.recording import BufferObject, BufferCodec, get_recording_from_file
from lib.requesters.protocols import RequesterProtocol
from lib.wrappers.schedulers import TaskScheduler

from .protocols import AdaptorProtocol

from pathlib import Path
from typing import Any, Callable, Generator, Dict, Sequence, Type, Optional, AsyncIterator


def not_implemented_callable(*args, **kwargs) -> None:
    raise NotImplementedError


msg_obj_cv = contextvars.ContextVar('msg_obj_cv')


@dataclass
class BaseAdaptorProtocol(AdaptorProtocol, Protocol):
    dataformat: Type[BaseMessageObject]
    bufferformat: Type[BufferObject] = BufferObject
    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger = field(default_factory=connection_logger_cv.get, compare=False, hash=False)
    context: Dict[str, Any] = field(default_factory=context_cv.get)
    preaction: ActionProtocol = None
    send: Callable[[bytes], None] = field(default=not_implemented_callable, repr=False, compare=False)
    timeout: int = 5

    def __post_init__(self) -> None:
        context_cv.set(self.context)
        self.codec: BaseCodec = self.dataformat.get_codec()
        self.buffer_codec: BufferCodec = self.bufferformat.get_codec()
        self.logger.new_connection()

    def on_msg_sent(self, msg_encoded: bytes, task: Optional[asyncio.Future]):
        self.logger.on_msg_sent(msg_encoded)

    def send_data(self, msg_encoded: bytes) -> None:
        self.logger.on_sending_encoded_msg(msg_encoded)
        fut = self.send(msg_encoded)
        if fut:
            fut.add_done_callback(partial(self.on_msg_sent, msg_encoded))
        else:
            self.on_msg_sent(msg_encoded, None)

    def _encode_msg(self, decoded: Any) -> MessageObjectType:
        return self.codec.from_decoded(decoded)

    def encode_and_send_msg(self, msg_decoded: Any) -> None:
        self.logger.on_sending_decoded_msg(msg_decoded)
        msg_obj = self._encode_msg(msg_decoded)
        self.send_data(msg_obj.encoded)

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None:
        for decoded_msg in decoded_msgs:
            self.encode_and_send_msg(decoded_msg)

    async def _run_preaction(self, buffer: bytes, timestamp: datetime = None) -> None:
        self.logger.info('Running preaction')
        buffer_obj = self.buffer_codec.from_decoded(buffer, received_timestamp=timestamp)
        await self.preaction.do_one(buffer_obj)

    def on_data_received(self, buffer: bytes, timestamp: datetime = None) -> asyncio.Future:
        self.logger.on_buffer_received(buffer)
        timestamp = timestamp or datetime.now()
        if self.preaction:
            self._scheduler.task_with_callback(self._run_preaction(buffer, timestamp),
                                               name=f"{self.context['peer']}-Preaction")
        msgs_generator = self.codec.decode_buffer(buffer, received_timestamp=timestamp)
        task = self._scheduler.task_with_callback(self.process_msgs(msgs_generator, buffer), name='Process_Msgs')
        return task

    async def close(self, exc: Optional[BaseException] = None) -> None:
        await asyncio.wait_for(self._scheduler.close(), timeout=self.timeout)
        self.logger.connection_finished(exc)

    @abstractmethod
    async def process_msgs(self, msgs: AsyncIterator[MessageObjectType], buffer: bytes) -> int: ...


@dataclass
class SenderAdaptor(BaseAdaptorProtocol):
    is_receiver = False
    requester: RequesterProtocol = None

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

    def all_notifications(self) -> Generator[MessageObjectType, None, None]:
        for i in range(0, self._notification_queue.qsize()):
            yield self._notification_queue.get_nowait()

    async def close(self, exc: Optional[BaseException] = None) -> None:
        exc = exc or RemoteConnectionClosedError()
        self._scheduler.cancel_all_futures(exc)
        await super().close(exc)

    async def send_data_and_wait(self, request_id: Any, encoded: bytes) -> Any:
        return await self._scheduler.run_wait_fut(request_id, self.send_data, encoded)

    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future:
        return await self.send_data_and_wait(msg_obj.request_id, msg_obj.encoded)

    async def encode_send_wait(self, decoded: Any) -> asyncio.Future:
        msg_obj = self._encode_msg(decoded)
        return await self.send_msg_and_wait(msg_obj)

    def _run_method(self, method: Callable, *args, **kwargs) -> None:
        msg_decoded = method(*args, **kwargs)
        self.encode_and_send_msg(msg_decoded)

    async def _run_method_and_wait(self, method: Callable, *args, **kwargs) -> asyncio.Future:
        msg_decoded = method(*args, **kwargs)
        return await self.encode_send_wait(msg_decoded)

    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None:
        prev_timestamp = None
        self.logger.debug("Playing recording from file %s", file_path)
        async for packet in get_recording_from_file(file_path):
            if (not hosts or packet.sender in hosts) and not packet.sent_by_server:
                if timing:
                    if prev_timestamp:
                        timedelta = packet.timestamp - prev_timestamp
                        seconds = timedelta.total_seconds()
                        await asyncio.sleep(seconds)
                    prev_timestamp = packet.timestamp
                self.send_data(packet.data)
        self.logger.debug("Recording finished")

    async def process_msgs(self, msgs: AsyncIterator[MessageObjectType], buffer: bytes) -> int:
        async for msg in msgs:
            if msg.request_id:
                try:
                    self._scheduler.set_result(msg.request_id, msg)
                except KeyError:
                    self._notification_queue.put_nowait(msg)
            else:
                self._notification_queue.put_nowait(msg)
        return len(buffer)


@dataclass
class ReceiverAdaptor(BaseAdaptorProtocol):
    is_receiver = True
    action: ActionProtocol = None

    def __post_init__(self) -> None:
        self._loop_id = id(asyncio.get_event_loop())
        super().__post_init__()
        if self.action.supports_notifications:
            self._notifications_task = self._scheduler.task_with_callback(self._send_notifications(), name='Notifications')
        else:
            self._notifications_task = None

    async def close(self, exc: Optional[BaseException] = None) -> None:
        if self._notifications_task:
            self._notifications_task.cancel()
        await super().close(exc)

    async def _send_notifications(self):
        async for item in self.action.get_notifications(self.context['peer']):
            self.encode_and_send_msg(item)

    def _on_exception(self, exc: BaseException, msg_obj: MessageObjectType) -> None:
        self.logger.on_msg_failed(msg_obj, exc)
        response = self.action.on_exception(msg_obj, exc)
        if response:
            self.encode_and_send_msg(response)

    def _on_success(self, result: Any, msg_obj: MessageObjectType) -> None:
        try:
            if result:
                self.encode_and_send_msg(result)
        finally:
            self.logger.on_msg_processed(msg_obj)

    def _on_decoding_error(self, buffer: bytes, exc: BaseException):
        self.logger.manage_error(exc)
        response = self.action.on_decode_error(buffer, exc)
        if response:
            self.encode_and_send_msg(response)

    async def _process_msg(self, msg_obj):
        try:
            result = await self.action.do_one(msg_obj)
            self._on_success(result, msg_obj)
        except BaseException as e:
            self._on_exception(e, msg_obj)

    async def process_msgs(self, msgs: AsyncIterator[MessageObjectType], buffer: bytes) -> int:
        tasks = []
        try:
            async for msg_obj in msgs:
                if not self.action.filter(msg_obj):
                    tasks.append(asyncio.create_task(self._process_msg(msg_obj)))
                else:
                    self.logger.on_msg_filtered(msg_obj)
            await asyncio.wait(tasks)
        except Exception as exc:
            self._on_decoding_error(buffer, exc)
        return len(buffer)
