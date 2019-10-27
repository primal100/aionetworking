from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .logging import BaseLogger, ConnectionLogger


LoggerType = TypeVar('LoggerType', bound='BaseLogger')
ConnectionLoggerType = TypeVar('ConnectionLoggerType', bound='ConnectionLogger')
