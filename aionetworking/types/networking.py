from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar
from aionetworking.compatibility import TypedDict

if TYPE_CHECKING:
    from aionetworking.networking.protocols import (ProtocolFactoryProtocol, ConnectionProtocol, NetworkConnectionProtocol,
                                                    UDPConnectionProtocol, AdaptorProtocol, SenderAdaptorProtocol,
                                                    SimpleNetworkConnectionProtocol)


ProtocolFactoryType = TypeVar('ProtocolFactoryType', bound='ProtocolFactoryProtocol')
ConnectionType = TypeVar('ConnectionType', bound='ConnectionProtocol')
NetworkConnectionType = TypeVar('NetworkConnectionType', bound='NetworkConnectionProtocol')
UDPConnectionType = TypeVar('UDPConnectionType', bound='UDPConnectionProtocol')
AdaptorType = TypeVar('AdaptorType', bound='AdaptorProtocol')
SenderAdaptorType = TypeVar('SenderAdaptorType', bound='SenderAdaptorProtocol')
SimpleNetworkConnectionType = TypeVar('SimpleNetworkConnectionType', bound='SimpleNetworkConnectionProtocol')


class BaseContext(TypedDict):
    protocol_name: str
    address: str
    peer: str
    own: str
    alias: str
    server: str
    client: str


class AFINETContext(BaseContext):
    host: str
    port: int


class SFTPContext(AFINETContext):
    username: str


class AFUNIXContext(BaseContext):
    fd: int


class NamedPipeContext(BaseContext):
    handle: int
