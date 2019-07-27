from __future__ import annotations
import asyncio
from abc import abstractmethod
from datetime import datetime
from typing import Any, AnyStr, AsyncGenerator, Generator, List, Optional, Sequence, TypeVar, Tuple, Union
from typing_extensions import Protocol
from pathlib import Path

from lib.formats.base import MessageObjectType
from lib.utils import inherit_on_type_checking_only


class ConnectionGeneratorProtocol(Protocol):

    @abstractmethod
    def __call__(self) -> Union[ConnectionGeneratorProtocol, NetworkConnectionProtocol]: ...

    @abstractmethod
    def is_owner(self, connection: NetworkConnectionProtocol) -> bool: ...

    @abstractmethod
    async def close(self, timeout: Union[int, float] = None) -> None: ...


ConnectionGeneratorType = TypeVar('ConnectionGeneratorType', bound=ConnectionGeneratorProtocol)


class ConnectionProtocol(Protocol):
    parent: int

    @abstractmethod
    def send(self, data: AnyStr) -> None: ...

    @abstractmethod
    def send_many(self, data_list: List[AnyStr]) -> None: ...

    @abstractmethod
    def clone(self: ConnectionType, *args, **kwargs) -> ConnectionType: ...

    @abstractmethod
    def is_child(self, parent_id: int) -> bool: ...

    @abstractmethod
    def finish_connection(self, exc: Optional[BaseException]) -> asyncio.Task: ...

    @abstractmethod
    async def close_wait(self, exc: Optional[BaseException]) -> asyncio.Task: ...


ConnectionType = TypeVar('ConnectionType', bound=ConnectionProtocol)


class NetworkConnectionMixinProtocol(Protocol):
    peer_str: str

    @abstractmethod
    def initialize_connection(self, peer: Tuple[str, int], sock:  Tuple[str, int], ) -> bool: ...


class NetworkConnectionProtocol(NetworkConnectionMixinProtocol, ConnectionProtocol, Protocol): ...


NetworkConnectionProtocolType = TypeVar('NetworkConnectionProtocolType', bound=NetworkConnectionProtocol)


class UDPConnectionMixinProtocol(Protocol):
    def set_transport(self, transport: asyncio.DatagramTransport): ...


class UDPConnectionProtocol(UDPConnectionMixinProtocol, NetworkConnectionProtocol, Protocol):  ...


UDPConnectionType = TypeVar('UDPConnectionType', bound=UDPConnectionProtocol)


class BaseAdaptorProtocol(Protocol):
    is_receiver: bool

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
    def on_data_received(self, buffer: AnyStr, timestamp: datetime = None) -> None: ...


class AdaptorProtocol(BaseAdaptorProtocol, Protocol):

    @abstractmethod
    async def close(self, exc: Optional[BaseException], timeout: Union[int, float]) -> None: ...


AdaptorProtocolType = TypeVar('AdaptorProtocolType', bound=AdaptorProtocol)


@inherit_on_type_checking_only
class AdaptorProtocolGetattr(BaseAdaptorProtocol, Protocol):

    def send_data(self, msg_encoded: AnyStr) -> None: ...

    def send_hex(self, hex_msg: AnyStr) -> None: ...

    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None: ...

    def encode_msg(self, decoded: Any) -> MessageObjectType: ...

    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None: ...

    def on_data_received(self, buffer: AnyStr, timestamp: datetime = None) -> None: ...


class SenderAdaptorMixinProtocol(Protocol):
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
    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None: ...


class SenderAdaptorProtocol(ConnectionProtocol, NetworkConnectionMixinProtocol, Protocol): ...


SenderAdaptorProtocolType = TypeVar('SenderAdaptorProtocolType', bound=SenderAdaptorProtocol)


@inherit_on_type_checking_only
class SenderAdaptorGetattr(SenderAdaptorMixinProtocol, Protocol):
    async def wait_notification(self) -> MessageObjectType: ...

    def get_notification(self) -> MessageObjectType: ...

    async def wait_notifications(self) -> AsyncGenerator[MessageObjectType, None]: ...

    def all_notifications(self) -> Generator[MessageObjectType, None, None]: ...

    async def send_data_and_wait(self, request_id: Any, encoded: AnyStr) -> asyncio.Future: ...

    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future: ...

    async def encode_send_wait(self, decoded: Any) -> asyncio.Future: ...

    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None: ...
