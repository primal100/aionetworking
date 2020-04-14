from abc import abstractmethod
from dataclasses import dataclass, field

from aionetworking.compatibility import Protocol
from aionetworking.logging.loggers import Logger, get_connection_logger_sender


@dataclass
class RequesterProtocol(Protocol):
    name = 'sender'
    methods = ()
    notification_methods = ()

    logger: Logger = field(default_factory=get_connection_logger_sender, compare=False)

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def close(self): ...
