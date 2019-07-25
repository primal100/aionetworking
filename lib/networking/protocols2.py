from __future__ import annotations
import asyncio
from abc import abstractmethod
from typing import Any, AnyStr, AsyncGenerator, Callable, Generator, Iterator, Sequence, TypeVar, Tuple
from typing_extensions import Protocol
from pathlib import Path

from lib.formats.base import MessageObjectType
from lib.utils import inherit_on_type_checking_only


class DataProtocol(Protocol):

    @abstractmethod
    def check_peer(self, other_ip) -> str: ...

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
    def send_many(self, data_list: Sequence[AnyStr]): ...

    @abstractmethod
    def send(self, data: AnyStr) -> None: ...


@inherit_on_type_checking_only
class DataProtocolGetattr(DataProtocol, Protocol):

    def check_peer(self, other_ip) -> str: ...

    def send_data(self, msg_encoded: AnyStr) -> None: ...

    def send_hex(self, hex_msg: AnyStr) -> None: ...

    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None: ...

    def encode_msg(self, decoded: Any) -> MessageObjectType: ...

    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None: ...

    def send_many(self, data_list: Sequence[AnyStr]): ...

    def send(self, data: AnyStr) -> None: ...


class NetworkProtocol(Protocol):

    @abstractmethod
    def close_connection(self) -> None: ...

    @abstractmethod
    def initialize(self, sock: Tuple[str, int], peer: Tuple[str, int]) -> bool: ...

    @abstractmethod
    def connection_made(self, transport: asyncio.BaseTransport) -> None: ...

    @abstractmethod
    def connection_lost(self, exc) -> None: ...


@inherit_on_type_checking_only
class NetworkProtocolGetattr(NetworkProtocol, Protocol):

    def close_connection(self) -> None: ...

    def initialize(self, sock: Tuple[str, int], peer: Tuple[str, int]) -> bool: ...

    def connection_made(self, transport: asyncio.BaseTransport) -> None: ...

    def connection_lost(self, exc) -> None: ...


class TCPProtocol(Protocol):

    @abstractmethod
    def data_received(self, data: AnyStr) -> None: ...


@inherit_on_type_checking_only
class TCPProtocolGetattr(NetworkProtocolGetattr, TCPProtocol, Protocol):

    def data_received(self, data: AnyStr) -> None: ...


class UDPProtocol(Protocol):

    @abstractmethod
    def datagram_received(self, data: AnyStr, addr: str): ...


@inherit_on_type_checking_only
class UDPProtocolGetattr(NetworkProtocolGetattr, UDPProtocol, Protocol):

    def datagram_received(self, data: AnyStr, addr: str): ...


class AdaptorProtocol(Protocol):

    @abstractmethod
    def on_data_received(self, buffer: AnyStr) -> None: ...

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


class SenderAdaptorProtocol(AdaptorProtocol, Protocol):

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


class ServerAdaptorProtocol(Protocol):

    @abstractmethod
    def process_msgs(self, msgs: Iterator[MessageObjectType], buffer: AnyStr) -> None: ...


ProtocolType = TypeVar('ProtocolType', bound=DataProtocol)
SenderAdaptorType = TypeVar('SenderAdaptorType', bound=SenderAdaptorProtocol)
ServerAdaptorType = TypeVar('ServerAdaptorType', bound=ServerAdaptorProtocol)
