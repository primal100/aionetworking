from logging import Filter, Logger, LogRecord

from dataclasses import field
from pydantic.dataclasses import dataclass
from lib.types import Expression

from lib import definitions
from typing import Type, List


@dataclass
class BaseFilter(Filter):

    loggers: List[Logger] = field(default_factory=list)

    def __init__(self, *args, loggers: List[Logger] = (), **kwargs):
        super().__init__(*args, **kwargs)
        self.loggers = loggers
        self.__post_init__()

    def __post_init__(self):
        for logger in self.loggers:
            logger.addFilter(self)

    @classmethod
    def swap_cls(cls, name: str) -> Type['BaseFilter']:
        return definitions.LOG_FILTERS[name]


@dataclass
class SenderFilter(BaseFilter):
    senders: List[str] = field(default_factory=list)

    def __init__(self, *args, senders: List[str] = (), **kwargs):
        super().__init__(*args, **kwargs)
        self.senders = senders

    def filter(self, record: LogRecord) -> bool:
        sender = getattr(record, 'sender', None)
        if not sender:
            msg_obj = getattr(record, 'msg_obj', None)
            if msg_obj:
                sender = msg_obj.sender
        if sender:
            return sender in self.senders
        return True


@dataclass
class MessageFilter(BaseFilter):

    expr: Expression

    def filter(self, record: LogRecord) -> bool:
        msg_obj = getattr(record, 'msg_obj', None)
        if msg_obj:
            return self.expr(msg_obj)
        return True
