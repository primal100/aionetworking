from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial

from .exceptions import MethodNotFoundError
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
from typing import Any, Callable, Iterator, Generator, Dict, Sequence, Type, Optional


def not_implemented_callable(*args, **kwargs) -> None:
    raise NotImplementedError


@dataclass
class BaseAdaptorProtocol(AdaptorProtocol, Protocol):
    dataformat: Type[BaseMessageObject]
    bufferformat: Type[BufferObject] = BufferObject
    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger = field(default_factory=connection_logger_cv.get, compare=False, hash=False)
    context: Dict[str, Any] = field(default_factory=context_cv.get)
    preaction: ActionProtocol = None
    send: Callable[[bytes], None] = field(default=not_implemented_callable, repr=False, compare=False)

    def __post_init__(self) -> None:
        context_cv.set(self.context)
        self.codec: BaseCodec = self.dataformat.get_codec()
        self.buffer_codec: BufferCodec = self.bufferformat.get_codec()
        self.logger.new_connection()

    def send_data(self, msg_encoded: bytes) -> None:
        self.logger.on_sending_encoded_msg(msg_encoded)
        self.send(msg_encoded)
        self.logger.on_msg_sent(msg_encoded)

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
        buffer_obj = self.buffer_codec.from_decoded(buffer, received_timestamp=timestamp)
        await self.preaction.do_one(buffer_obj)

    def on_data_received(self, buffer: bytes, timestamp: datetime = None) -> None:
        self.logger.on_buffer_received(buffer)
        timestamp = timestamp or datetime.now()
        if self.preaction:
            self._scheduler.task_with_callback(self._run_preaction(buffer, timestamp), name=f"{self.context['peer']}-Preaction")
        msgs_generator = self.codec.decode_buffer(buffer, received_timestamp=timestamp)
        self.process_msgs(msgs_generator, buffer)

    async def close(self, exc: Optional[BaseException] = None) -> None:
        await self._scheduler.close()
        self.logger.connection_finished(exc)

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: bytes) -> None: ...


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
        last_timestamp = None
        self.logger.debug("Playing recording from file %s", file_path)
        async for packet in get_recording_from_file(file_path):
            if (not hosts or packet.sender in hosts) and not packet.sent_by_server:
                if timing:
                    if last_timestamp:
                        timedelta = packet.timestamp - last_timestamp
                        seconds = timedelta.total_seconds()
                        await asyncio.sleep(seconds)
                    last_timestamp = packet.timestamp
                self.send_data(packet.data)
        self.logger.debug("Recording finished")

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: bytes) -> None:
        for msg in msgs:
            if msg.request_id:
                self._scheduler.set_result(msg.request_id, msg)
            else:
                self._notification_queue.put_nowait(msg)


@dataclass
class ReceiverAdaptor(BaseAdaptorProtocol):
    is_receiver = True
    action: ActionProtocol = None

    def _on_exception(self, exc: BaseException, msg_obj: MessageObjectType) -> None:
        try:
            self.logger.manage_error(exc)
            response = self.action.on_exception(msg_obj, exc)
            if response:
                self.encode_and_send_msg(response)
        finally:
            self.logger.on_msg_processed(msg_obj)

    def _on_success(self, result, msg_obj: MessageObjectType = None) -> None:
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

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: bytes) -> None:
        try:
            for msg_obj in msgs:
                if not self.action.filter(msg_obj):
                    self._scheduler.create_promise(self.action.do_one(msg_obj), self._on_success, self._on_exception,
                                                   task_name=f"{self.context['peer']}-Process-id-{msg_obj.uid}",
                                                   msg_obj=msg_obj)
                    self.logger.debug('Task created for %s', msg_obj.uid)
                else:
                    self.logger.on_msg_filtered(msg_obj)
        except Exception as exc:
            self._on_decoding_error(buffer, exc)
