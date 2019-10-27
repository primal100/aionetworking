from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .protocols import MessageObject, Codec


MessageObjectType = TypeVar('MessageObjectType', bound='MessageObject')
CodecType = TypeVar('CodecType', bound='Codec')