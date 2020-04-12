
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aionetworking.senders.protocols import SenderProtocol


SenderType = TypeVar('SenderType', bound='SenderProtocol')
