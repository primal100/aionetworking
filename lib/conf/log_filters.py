import logging
import operator
from dataclasses import field

from lib.conf.types import BaseSwappable, ListLoggers, ListStrings, Operator, DataType
from lib import definitions
from typing import Type, Callable


class _BaseFilter(BaseSwappable):
    name = ''
    config_section = 'filter'

    #Dataclass fields
    loggers: ListLoggers = []

    def __post_init__(self):
        super().__init__()
        super().__post_init__()
        for logger in self.loggers:
            logger.addFilter(self)


class BaseFilter(_BaseFilter, logging.Filter):

    @classmethod
    def get_swappable(cls, name : str) -> Type[_BaseFilter]:
        return definitions.LOG_FILTERS[name]


class SenderFilter(BaseFilter):
    #Dataclass fields
    senders: ListStrings = []

    def filter(self, record: logging.LogRecord) -> bool:
        sender = getattr(record, 'sender', None)
        if not sender:
            msg_obj = getattr(record, 'msg_obj', None)
            if msg_obj:
                sender = msg_obj.sender
                return sender in self.senders
            return True
        return sender in self.senders


class MessageFilter(BaseFilter):

    #Dataclass fields
    attr: str = None
    operator: Callable = field(default=operator.eq, metadata={'factory': Operator})
    value_type: DataType = str
    value: str = field(default=None, metadata={'type_depends_on': 'value_type'})
    case_sensitive: bool = True

    def filter(self, record: logging.LogRecord) -> bool:
        msg_obj = getattr(record, 'msg_obj', None)
        if msg_obj:
            value = getattr(msg_obj, self.attr, None)
            data_type = type(value)
            if self.case_sensitive or not data_type == str:
                return self.operator(value, data_type(self.value))
            return self.operator(value.lower(), self.value.lower())
        return True
