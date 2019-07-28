from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .protocols import (ConnectionGeneratorProtocol, ConnectionProtocol, NetworkConnectionProtocol,
                            UDPConnectionProtocol, AdaptorProtocol, SenderAdaptorProtocol,
                            SimpleNetworkConnectionProtocol)


ConnectionGeneratorType = TypeVar('ConnectionGeneratorType', bound='ConnectionGeneratorProtocol')
ConnectionType = TypeVar('ConnectionType', bound='ConnectionProtocol')
NetworkConnectionType = TypeVar('NetworkConnectionType', bound='NetworkConnectionProtocol')
UDPConnectionType = TypeVar('UDPConnectionType', bound='UDPConnectionProtocol')
AdaptorType = TypeVar('AdaptorType', bound='AdaptorProtocol')
SenderAdaptorType = TypeVar('SenderAdaptorType', bound='SenderAdaptorProtocol')
SimpleNetworkConnectionType = TypeVar('SimpleNetworkConnectionType', bound='SimpleNetworkConnectionProtocol')