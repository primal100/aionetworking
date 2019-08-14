from __future__ import annotations
import asyncio
from abc import abstractmethod
from datetime import datetime
from typing import Any, AnyStr, AsyncGenerator, Generator, Optional, Sequence, TypeVar, Union
from lib.compatibility import Protocol
from pathlib import Path

from lib.conf.logging import Logger
from lib.formats.base import MessageObjectType
from lib.utils import inherit_on_type_checking_only

from typing import Tuple


class ProtocolFactoryProtocol(Protocol):

    @abstractmethod
    def __call__(self) -> Union[ProtocolFactoryProtocol, NetworkConnectionProtocol]: ...

    @abstractmethod
    def is_owner(self, connection: NetworkConnectionProtocol) -> bool: ...

    @abstractmethod
    def set_logger(self, logger: Logger): ...

    @abstractmethod
    def set_name(self, name: str, peer_prefix: str): ...

    @abstractmethod
    async def wait_all_closed(self) -> None: ...

    @abstractmethod
    async def wait_num_has_connected(self, num: int) -> None: ...

    @abstractmethod
    async def wait_all_messages_processed(self) -> None: ...


class ConnectionProtocol(Protocol):
    parent_name: str

    def set_logger(self, logger: Logger) -> None: ...

    @abstractmethod
    def send(self, data: AnyStr) -> None: ...

    @abstractmethod
    def clone(self: ConnectionType, **kwargs) -> ConnectionType: ...

    @abstractmethod
    def is_child(self, parent_name: str) -> bool: ...

    @abstractmethod
    def initialize_connection(self, transport: asyncio.BaseTransport, peer: Tuple[str, int] = None) -> bool: ...

    @abstractmethod
    def finish_connection(self, exc: Optional[BaseException]) -> None: ...

    @abstractmethod
    async def close_wait(self): ...

    @abstractmethod
    async def wait_connected(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @property
    @abstractmethod
    def peer(self) -> str: ...


ConnectionType = TypeVar('ConnectionType', bound=ConnectionProtocol)


class NetworkConnectionMixinProtocol(Protocol):
    peer: str


class NetworkConnectionProtocol(NetworkConnectionMixinProtocol, ConnectionProtocol, Protocol): ...


NetworkConnectionProtocolType = TypeVar('NetworkConnectionProtocolType', bound=NetworkConnectionProtocol)


class SimpleNetworkConnectionProtocol(Protocol):
    peer: str
    parent_name: int

    @abstractmethod
    async def wait_all_messages_processed(self) -> None: ...

    @abstractmethod
    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...


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
    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...

    @abstractmethod
    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None: ...

    @abstractmethod
    def on_data_received(self, buffer: AnyStr, timestamp: datetime = None) -> None: ...


class AdaptorProtocol(BaseAdaptorProtocol, Protocol):

    @abstractmethod
    async def close_actions(self, exc: Optional[BaseException] = None) -> None: ...


AdaptorProtocolType = TypeVar('AdaptorProtocolType', bound=AdaptorProtocol)


@inherit_on_type_checking_only
class AdaptorProtocolGetattr(BaseAdaptorProtocol, Protocol):

    def send_data(self, msg_encoded: AnyStr) -> None: ...

    def send_hex(self, hex_msg: AnyStr) -> None: ...

    def send_hex_msgs(self, hex_msgs: Sequence[AnyStr]) -> None: ...

    def encode_and_send_msg(self, msg_decoded: Any) -> None: ...

    def encode_and_send_msgs(self, decoded_msgs: Sequence[Any]) -> None: ...

    def on_data_received(self, buffer: AnyStr, timestamp: datetime = None) -> None: ...


class SenderAdaptorMixinProtocol(Protocol):
    @abstractmethod
    async def wait_notification(self) -> MessageObjectType: ...

    @abstractmethod
    def get_notification(self) -> MessageObjectType: ...

    @abstractmethod
    async def wait_notifications(self) -> AsyncGenerator[MessageObjectType, None]:
        yield

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

    async def wait_notifications(self) -> AsyncGenerator[MessageObjectType, None]:
        yield

    def all_notifications(self) -> Generator[MessageObjectType, None, None]: ...

    async def send_data_and_wait(self, request_id: Any, encoded: AnyStr) -> asyncio.Future: ...

    async def send_msg_and_wait(self, msg_obj: MessageObjectType) -> asyncio.Future: ...

    async def encode_send_wait(self, decoded: Any) -> asyncio.Future: ...

    async def play_recording(self, file_path: Path, hosts: Sequence = (), timing: bool = True) -> None: ...
