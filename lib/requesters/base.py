from __future__ import annotations
from abc import ABC

from lib.conf.logging import Logger

from dataclasses import dataclass


@dataclass
class BaseRequester(ABC):
    name = 'sender'
    methods = ()
    notification_methods = ()

    logger: Logger = Logger('sender')

    @classmethod
    def swap_cls(cls, name: str):
        from lib import definitions
        return definitions.REQUESTERS[name]

