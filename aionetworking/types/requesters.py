from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aionetworking.requesters.protocols import RequesterProtocol


RequesterType = TypeVar('RequesterType', bound='RequesterProtocol')

