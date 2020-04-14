
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aionetworking.actions.protocols import ActionProtocol


ActionType = TypeVar('ActionType', bound='ActionProtocol')

