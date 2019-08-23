from __future__ import annotations

from lib.conf.logging import Logger, get_connection_logger_sender

from dataclasses import dataclass, field
from lib.compatibility import Protocol


@dataclass
class RequesterProtocol(Protocol):
    name = 'sender'
    methods = ()
    notification_methods = ()

    logger: Logger = field(default_factory=get_connection_logger_sender, compare=False)

    @classmethod
    def swap_cls(cls, name: str):
        from lib import definitions
        return definitions.REQUESTERS[name]