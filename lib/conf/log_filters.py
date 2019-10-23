from logging import Filter, Logger, LogRecord

from dataclasses import dataclass
from lib.types import Expression

from typing import Sequence


@dataclass
class BaseFilter(Filter):

    loggers: Sequence[Logger]

    def __init__(self, loggers: Sequence[Logger] = (), *args,  **kwargs):
        super().__init__(*args, **kwargs)
        self.loggers = loggers
        self.__post_init__()

    def __post_init__(self):
        for logger in self.loggers:
            logger.addFilter(self)


@dataclass
class PeerFilter(BaseFilter):
    peers: Sequence[str]

    def __init__(self, peers: Sequence[str], *args, **kwargs):
        self.peers = peers
        super().__init__(*args, **kwargs)

    def filter(self, record: LogRecord) -> bool:
        peer = getattr(record, 'alias', None)
        if peer:
            return peer in self.peers
        return True


@dataclass
class MessageFilter(BaseFilter):

    expr: Expression

    def __init__(self, expr: Expression, *args, **kwargs):
        self.expr = expr
        super().__init__(*args, **kwargs)

    def filter(self, record: LogRecord) -> bool:
        msg_obj = getattr(record, 'msg_obj', None)
        if msg_obj:
            return self.expr(msg_obj)
        return True
