from __future__ import annotations
import asyncio
from abc import abstractmethod
from typing import Any, AnyStr, AsyncGenerator, Callable, Generator, Iterator, List, Sequence, TypeVar, Tuple
from typing_extensions import Protocol
from pathlib import Path

from lib.formats.base import MessageObjectType
from lib.utils import inherit_on_type_checking_only


ProtocolType = TypeVar('ProtocolType', bound='BaseProtocol')


class DataProtocol(Protocol):

    @abstractmethod
    def send(self, data: AnyStr) -> None: ...

    @abstractmethod
    def send_many(self, data_list: List[AnyStr]) -> None: ...


class NetworkProtocol(Protocol):

    @abstractmethod
    def connection_made(self, transport) -> None: ...

    @abstractmethod
    def close_connection(self) -> None: ...

    @abstractmethod
    def connection_lost(self, exc: BaseException) -> None: ...

    @abstractmethod
    def initialize(self, sock: Tuple[str, int], peer: Tuple[str, int]) -> bool: ...


class AdaptorProtocol(Protocol):

    @abstractmethod
    def send_data(self, msg_encoded: AnyStr) -> None: ...

    @abstractmethod
    def send_hex(self, hex_msg: AnyStr) -> None: ...

    @abstractmethod
    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None: ...

    @abstractmethod
    def encode_msg(self, decoded: Any) -> MessageObjectType: ...

    @abstractmethod
    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...

    @abstractmethod
    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


@inherit_on_type_checking_only
class AdaptorProtocolGetattr(AdaptorProtocol, Protocol):

    def send_data(self, msg_encoded: AnyStr) -> None: ...

    def send_hex(self, hex_msg: AnyStr) -> None: ...

    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None: ...

    def encode_msg(self, decoded: Any) -> MessageObjectType: ...

    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None: ...

    async def close(self) -> None: ...


class ReceiverAdaptor(AdaptorProtocol, Protocol):

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


@inherit_on_type_checking_only
class ReceiverAdaptorGetattr(ReceiverAdaptor, Protocol):

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


class SenderAdaptor(Protocol):
    @abstractmethod
    async def wait_notification(self) -> MessageObjectType: ...

    @abstractmethod
    def get_notification(self) -> MessageObjectType: ...

    @abstractmethod
    async def wait_notifications(self) -> AsyncGenerator[MessageObjectType, None]: ...

    @abstractmethod
    def all_notifications(self) -> Generator[MessageObjectType, None, None]: ...

    @abstractmethod
    async def send_data_and_wait(self, request_id: Any, encoded: AnyStr) -> asyncio.Future: ...

    @abstractmethod
    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future: ...

    @abstractmethod
    async def encode_send_wait(self, decoded: Any) -> asyncio.Future: ...

    @abstractmethod
    def run_method(self, method: Callable, *args, **kwargs) -> None: ...

    @abstractmethod
    async def run_method_and_wait(self, method: Callable, *args, **kwargs) -> asyncio.Future: ...

    @abstractmethod
    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None: ...

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


@inherit_on_type_checking_only
class SenderAdaptorGetattr(SenderAdaptor):
    async def wait_notification(self) -> MessageObjectType: ...

    def get_notification(self) -> MessageObjectType: ...

    async def wait_notifications(self) -> AsyncGenerator[MessageObjectType, None]: ...

    def all_notifications(self) -> Generator[MessageObjectType, None, None]: ...

    async def send_data_and_wait(self, request_id: Any, encoded: AnyStr) -> asyncio.Future: ...

    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future: ...

    async def encode_send_wait(self, decoded: Any) -> asyncio.Future: ...

    def run_method(self, method: Callable, *args, **kwargs) -> None: ...

    async def run_method_and_wait(self, method: Callable, *args, **kwargs) -> asyncio.Future: ...

    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None: ...

    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


class BaseServerProtocol:

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


class BaseTwoWayServerProtocol(Protocol):

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...