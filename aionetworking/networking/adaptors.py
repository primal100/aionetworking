from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field
import datetime
from functools import partial

from .exceptions import MethodNotFoundError, RemoteConnectionClosedError
from aionetworking.actions.protocols import ActionProtocol
from aionetworking.compatibility import Protocol, create_task
from aionetworking.logging.loggers import ConnectionLogger, get_connection_logger_receiver
from aionetworking.logging.utils_logging import p
from aionetworking.types.formats import MessageObjectType, CodecType
from aionetworking.types.networking import BaseContext
from aionetworking.formats.recording import BufferObject, BufferCodec, get_recording_from_file
from aionetworking.requesters.protocols import RequesterProtocol
from aionetworking.futures.schedulers import TaskScheduler

from .protocols import AdaptorProtocol

from pathlib import Path
from typing import Any, Callable, Generator, Dict, Sequence, Type, AsyncIterator, Optional


def not_implemented_callable(*args, **kwargs) -> None:
    raise NotImplementedError


@dataclass
class BaseAdaptorProtocol(AdaptorProtocol, Protocol):
    dataformat: Type[MessageObjectType]
    bufferformat: Type[BufferObject] = BufferObject
    codec: CodecType = None
    buffer_codec: BufferCodec = None
    _scheduler: TaskScheduler = field(default_factory=TaskScheduler, init=False, hash=False, compare=False, repr=False)
    logger: ConnectionLogger = field(default_factory=get_connection_logger_receiver, compare=False, hash=False)
    context: BaseContext = field(default_factory=dict)
    codec_config: Dict[str, Any] = field(default_factory=dict, metadata={'pickle': True})
    preaction: ActionProtocol = None
    send: Callable[[bytes], Optional[asyncio.Future]] = field(default=not_implemented_callable, repr=False, compare=False)

    def __post_init__(self) -> None:
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

    def _set_codecs(self, buffer: Optional[bytes]):
        self.codec = self.dataformat.get_codec(buffer, logger=self.logger, context=self.context, **self.codec_config)
        self.buffer_codec: BufferCodec = self.bufferformat.get_codec(buffer, context=self.context, logger=self.logger)

    def on_encode_task_finished(self, task: asyncio.Future):
        exception = task.exception()
        if exception:
            self.logger.manage_error(exception)
        else:
            msg_obj = task.result()
            self.logger.on_sending_decoded_msg(msg_obj)
            self.send_data(msg_obj.encoded)
        self._scheduler.task_done(task)

    def encode_and_send_msg(self, decoded: Any) -> None:
        if not self.codec:
            self._set_codecs(decoded)

        self._scheduler.task_with_callback(self.codec.encode_obj(decoded), callback=self.on_encode_task_finished)

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None:
        for decoded_msg in decoded_msgs:
            self.encode_and_send_msg(decoded_msg)

    async def _run_preaction(self, buffer: bytes, timestamp: datetime.datetime = None) -> None:
        self.logger.info('Running preaction')
        buffer_obj = await self.buffer_codec.encode_obj(buffer, system_timestamp=timestamp)
        if not self.preaction.filter(buffer_obj):
            await self.preaction.do_one(buffer_obj)

    def on_data_received(self, buffer: bytes, timestamp: datetime.datetime = None) -> asyncio.Future:
        timestamp = timestamp or datetime.datetime.now()
        if not self.codec:
            self._set_codecs(buffer)
        self.logger.on_buffer_received(buffer)
        if self.preaction:
            self._scheduler.task_with_callback(self._run_preaction(buffer, timestamp),
                                               name=f"{self.context['peer']}-Preaction")
        msgs_generator = self.codec.decode_buffer(buffer, system_timestamp=timestamp)
        task = self._scheduler.task_with_callback(self.process_msgs(msgs_generator, buffer), name='Process_Msgs')
        return task

    async def wait_current_tasks(self) -> None:
        await self._scheduler.wait_current_tasks()

    async def close(self, exc: Optional[BaseException] = None) -> None:
        self.logger.info('Connection waiting on %s to complete', p.no('task', self._scheduler.task_count))
        await self._scheduler.close()
        self.logger.connection_finished(exc)

    @abstractmethod
    async def process_msgs(self, msgs: AsyncIterator[MessageObjectType], buffer: bytes) -> None: ...


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
        self._scheduler.cancel_all_futures(RemoteConnectionClosedError)
        await super().close(exc)

    async def send_data_and_wait(self, request_id: Any, encoded: bytes) -> Any:
        return await self._scheduler.run_wait_fut(request_id, self.send_data, encoded)

    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future:
        return await self.send_data_and_wait(msg_obj.request_id, msg_obj.encoded)

    async def encode_send_wait(self, decoded: Any) -> asyncio.Future:
        if not self.codec:
            self._set_codecs(decoded)
        msg_obj = await self.codec.encode_obj(decoded)
        self.logger.on_sending_decoded_msg(msg_obj)
        return await self.send_msg_and_wait(msg_obj)

    def _run_method(self, method: Callable, *args, **kwargs) -> None:
        decoded = method(*args, **kwargs)
        self.encode_and_send_msg(decoded)

    async def _run_method_and_wait(self, method: Callable, *args, **kwargs) -> asyncio.Future:
        decoded = method(*args, **kwargs)
        return await self.encode_send_wait(decoded)

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

    async def process_msgs(self, msgs: AsyncIterator[MessageObjectType], buffer: bytes) -> None:
        async for msg in msgs:
            if msg.request_id is not None:
                try:
                    self._scheduler.set_result(msg.request_id, msg)
                except KeyError:
                    self._notification_queue.put_nowait(msg)
            else:
                self._notification_queue.put_nowait(msg)


@dataclass
class ReceiverAdaptor(BaseAdaptorProtocol):
    is_receiver = True
    action: ActionProtocol = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.action.supports_notifications:
            self._notifications_task = self._scheduler.task_with_callback(self._send_action_notifications(),
                                                                          continuous=True, name='Notifications')
        else:
            self._notifications_task = None

    def _set_codecs(self, buffer: Optional[bytes]):
        super()._set_codecs(buffer)
        if self.codec.supports_notifications and not self._notifications_task:
            self._notifications_task = self._scheduler.task_with_callback(self._send_codec_notifications(), continuous=True,
                                                                          name='Notifications')

    async def close(self, exc: Optional[BaseException] = None) -> None:
        if self._notifications_task:
            self._notifications_task.cancel()
        await super().close(exc)

    async def _send_action_notifications(self):
        async for item in self.action.get_notifications(self.context['peer']):
            self.encode_and_send_msg(item)

    async def _send_codec_notifications(self):
        async for item in self.codec.get_notifications():
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
        self.logger.manage_decode_error(buffer, exc)
        response = self.action.on_decode_error(buffer, exc)
        if response:
            self.encode_and_send_msg(response)

    async def _process_msg(self, msg_obj):
        self.logger.debug('Processing message %s', msg_obj)
        try:
            result = await self.action.do_one(msg_obj)
            self._on_success(result, msg_obj)
        except BaseException as e:
            self._on_exception(e, msg_obj)
            #raise

    async def process_msgs(self, msgs: AsyncIterator[MessageObjectType], buffer: bytes) -> None:
        tasks = []
        try:
            async for msg_obj in msgs:
                if not self.action.filter(msg_obj):
                    tasks.append(create_task(self._process_msg(msg_obj)))
                else:
                    self.logger.on_msg_filtered(msg_obj)
            await asyncio.wait(tasks)
        except Exception as exc:
            self._on_decoding_error(buffer, exc)
            raise

