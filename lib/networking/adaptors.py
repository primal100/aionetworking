from abc import abstractmethod
import asyncio
import aiofiles
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
import json
from lib.formats.contrib.json import JSONObject

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


encoded_msg = b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'


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
    received_bytes: int = 0
    expected_msgs: int = 50000
    expected_bytes: int = 3950000
    message_size: int = 79
    first: datetime = None
    last: datetime = None
    num_buffers: int = 0
    received_msgs: int = 0
    processed_msgs: int = 0

    def __post_init__(self) -> None:
        context_cv.set(self.context)
        #self.queue = asyncio.Queue()
        #asyncio.create_task(self.manage_file)
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
        self.logger.info('Running preaction')
        buffer_obj = self.buffer_codec.from_decoded(buffer, received_timestamp=timestamp)
        await self.preaction.do_one(buffer_obj)

    async def process_msgs(self, buffer: bytes, timestamp: datetime = None):
        self.num_buffers += 1
        if not self.first:
            self.first = datetime.now()
        buffer_len = len(buffer)
        num_msgs = round(buffer_len / self.message_size)
        coros = []
        self.received_msgs += num_msgs
        for i in range(0, num_msgs):
            coros.append(self.action.do_one(encoded_msg))
        await asyncio.wait(coros)
        self.processed_msgs += num_msgs
        self.last = datetime.now()
        if self.processed_msgs == self.expected_msgs:
            pass

    def _finish(self):
            print(f"Buffers received: {self.num_buffers}")
            print(f"Msgs per buffer: {self.num_buffers / self.expected_msgs}")
            interval = (self.last - self.first).total_seconds()
            print(f"{self.received_msgs} took {interval} seconds")
            print(f"Average:{self.received_msgs / interval}/s")

    def on_data_received(self, buffer: bytes, timestamp: datetime = None) -> None:
        task = self._scheduler.create_task(self.process_msgs(buffer, timestamp))
        task.add_done_callback(self._scheduler.task_done)
        """self.logger.on_buffer_received(buffer)
        #num = int(len(buffer) / 79)
        #self.logger.on_buffer_decoded(num)
        #self.logger.on_msg_processed({'jsonrpc': '2.0', 'id': 1, 'method': 'login', 'params': ['user1', 'password']})
        timestamp = timestamp or datetime.now()
        if self.preaction:
            self._scheduler.task_with_callback(self._run_preaction(buffer, timestamp),
                                               name=f"{self.context['peer']}-Preaction")
        msgs_generator = self.codec.decode_buffer(buffer, received_timestamp=timestamp)
        task = self._scheduler.create_task(self.process_msgs(msgs_generator, buffer))
        task.add_done_callback(self._scheduler.task_done)
        return task"""

    async def close(self, exc: Optional[BaseException] = None) -> None:
        await asyncio.wait_for(self._scheduler.close(), timeout=self.timeout)
        self.logger.connection_finished(exc)

    #@abstractmethod
    #async def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: bytes) -> int: ...


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

    async def close(self, exc: Optional[BaseException] = None) -> None:
        await super().close()
        self._finish()

    def _on_exception(self, exc: BaseException, msg_obj: MessageObjectType) -> None:
        try:
            self.logger.manage_error(exc)
            response = self.action.on_exception(msg_obj, exc)
            if response:
                self.encode_and_send_msg(response)
        finally:
            self.logger.on_msg_processed(msg_obj)

    def _on_success(self, result, msg_obj: MessageObjectType) -> None:
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

    """async def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: bytes) -> int:
        scheduler = TaskScheduler()
        try:
            for i, msg_obj in enumerate(msgs):
                if not self.action.filter(msg_obj):
                    scheduler.create_promise(self.action.do_one(msg_obj), self._on_success, self._on_exception,
                                                          task_name=f"{self.context['peer']}-Process-id-{msg_obj.uid}",
                                                          msg_obj=msg_obj)
                    self.logger.debug('Task created for %s', msg_obj.uid)
                else:
                    self.logger.on_msg_filtered(msg_obj)
            await scheduler.join()
        except Exception as exc:
            self._on_decoding_error(buffer, exc)
        return len(buffer)"""
