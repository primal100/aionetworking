import logging

from dataclasses import field
from pydantic.dataclasses import dataclass
from pydantic.utils import AnyCallable
from lib.conf.types import Logger, Expression

from lib import definitions
from typing import Type, List, Generator


CallableGenerator = Generator[AnyCallable, None, None]


class BaseFilter(logging.Filter):

    loggers: List[Logger] = []

    def __post_init__(self):
        for logger in self.loggers:
            logger.addFilter(self)

    @classmethod
    def swap_cls(cls, name: str) -> Type['BaseFilter']:
        return definitions.LOG_FILTERS[name]


@dataclass
class SenderFilter(BaseFilter):
    senders: List[str] = field(default_factory=list)

    def filter(self, record: logging.LogRecord) -> bool:
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

    def filter(self, record: logging.LogRecord) -> bool:
        msg_obj = getattr(record, 'msg_obj', None)
        if msg_obj:
            return self.expr(msg_obj)
        return True
