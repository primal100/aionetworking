
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aionetworking.logging.loggers import BaseLogger, ConnectionLogger


LoggerType = TypeVar('LoggerType', bound='BaseLogger')
ConnectionLoggerType = TypeVar('ConnectionLoggerType', bound='ConnectionLogger')