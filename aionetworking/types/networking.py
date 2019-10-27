from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

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
