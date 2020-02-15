from __future__ import annotations
from logging import Filter, LogRecord

from dataclasses import dataclass
from aionetworking.utils import Expression

from typing import Sequence


@dataclass
class PeerFilter(Filter):
    peers: Sequence[str]

    def __init__(self, peers: Sequence[str], *args, **kwargs):
        self.peers = peers
        super().__init__(*args, **kwargs)

    def filter(self, record: LogRecord) -> bool:
        address = getattr(record, 'address', None)
        host = getattr(record, 'host', None)
        if address or host:
            return any(s in self.peers for s in (address, host))
        return True


@dataclass
class MessageFilter(Filter):

    expr: Expression

    def __init__(self, expr: Expression, *args, **kwargs):
        self.expr = expr
        super().__init__(*args, **kwargs)

    def filter(self, record: LogRecord) -> bool:
        msg_obj = getattr(record, 'msg_obj', None)
        if msg_obj:
            return self.expr(msg_obj)
        return True
