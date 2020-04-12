
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aionetworking.receivers.protocols import ReceiverProtocol


ReceiverType = TypeVar('ReceiverType', bound='ReceiverProtocol')

