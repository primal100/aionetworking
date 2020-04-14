
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aionetworking.formats.protocols import MessageObject, Codec
    from aionetworking.formats.contrib.json import JSONObject


MessageObjectType = TypeVar('MessageObjectType', bound='MessageObject')
CodecType = TypeVar('CodecType', bound='Codec')
JSONObjectType = TypeVar('JSONObjectType', bound='JSONObject')