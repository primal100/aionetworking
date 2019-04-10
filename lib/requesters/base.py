from abc import ABC

from lib.conf.logging import Logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass


@dataclass
class BaseRequester(ABC):
    name = 'sender'
    methods = ()
    notification_methods = ()

    timeout: int = 5
    logger: Logger ='sender'

    @classmethod
    def swap_cls(cls, name: str):
        from lib import definitions
        return definitions.REQUESTERS[name]

