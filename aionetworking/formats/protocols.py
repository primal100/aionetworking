from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from pathlib import Path

from aionetworking.compatibility import Protocol

from typing import AsyncGenerator, Any, Dict, Sequence, Optional
from aionetworking.types.formats import CodecType, MessageObjectType


class MessageObject(Protocol):

    @classmethod
    @abstractmethod
    def _get_codec_kwargs(cls) -> Dict:
        return {}

    @classmethod
    @abstractmethod
    def get_codec(cls, first_buffer_received: Optional[bytes], **kwargs) -> CodecType: ...

    @property
    @abstractmethod
    def peer(self) -> str: ...

    @property
    @abstractmethod
    def uid(self) -> Any: ...

    @property
    @abstractmethod
    def request_id(self) -> Any: ...

    @property
    @abstractmethod
    def pformat(self) -> str: ...

    @property
    @abstractmethod
    def timestamp(self) -> datetime: ...

    @abstractmethod
    def filter(self) -> bool: ...


class Codec(Protocol):

    @abstractmethod
    async def decode(self, encoded: bytes, **kwargs) -> AsyncGenerator[Sequence[bytes, Any], None]:
        yield

    @abstractmethod
    def decode_one(self, encoded: bytes, **kwargs) -> Any: ...

    @abstractmethod
    def encode(self, decoded: Any, **kwargs) -> bytes: ...

    @abstractmethod
    async def decode_buffer(self, encoded: bytes, **kwargs) -> AsyncGenerator[MessageObjectType, None, None]:
        yield

    @abstractmethod
    def from_decoded(self, decoded: Any, **kwargs) -> MessageObjectType: ...

    @abstractmethod
    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        yield

    @abstractmethod
    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType: ...
