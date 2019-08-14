from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from collections import ChainMap
from datetime import datetime
from dataclasses import dataclass, field

#from pydantic import ValidationError

from lib.networking.connections_manager import connections_manager
from lib.utils import dataclass_getstate, dataclass_setstate
from lib.utils import log_exception, get_current_task_name
from lib.utils_logging import LoggingDatetime, LoggingTimeDelta, BytesSize, MsgsCount, p
from lib.wrappers.schedulers import TaskScheduler

from typing import ClassVar, Type, Optional, Dict, AnyStr, Iterable, Generator, Any, Union
from lib.formats.types import MessageObjectType
from .types import ConnectionLoggerType


@dataclass
class BaseLogger(logging.LoggerAdapter, ABC):
    logger_name: str
    datefmt: str
    extra: dict
    _is_closing: bool = field(default=False, init=False)

    def __init__(self, logger_name: str, datefmt: str = '%Y-%M-%d %H:%M:%S', extra: Dict = None):
        self.logger_name = logger_name
        self.datefmt = datefmt
        logger = logging.getLogger(logger_name)
        super().__init__(logger, extra or {})
        self.connection_logger_cls = self._get_connection_logger_cls()

    def manage_error(self, exc: BaseException) -> None:
        if exc:
            self.error(log_exception(exc))

    def manage_critical_error(self, exc: BaseException) -> None:
        if exc:
            self.critical(log_exception(exc))

    def __getstate__(self):
        state = dataclass_getstate(self)
        if self._is_closing:
            state['_is_closing'] = self._is_closing
        return state

    def __setstate__(self, state):
        self._is_closing = state.pop('_is_closing', self._is_closing)
        dataclass_setstate(self, state)

    @abstractmethod
    def _get_connection_logger_cls(self) -> Type: ...

    @abstractmethod
    def get_connection_logger(self, name: str = 'connection', **kwargs): ...

    @abstractmethod
    def get_child(self, name: str = '', cls: Type = None, **kwargs) -> BaseLogger: ...

    @abstractmethod
    def get_sibling(self, name: str = '', **kwargs) -> BaseLogger: ...

    @abstractmethod
    def _get_logger(self, name: str = '', cls: Type[BaseLogger] = None, extra: Dict[str, Any] = None, **kwargs) -> Any: ...


@dataclass
class Logger(BaseLogger):
    _loggers: ClassVar = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process(self, msg, kwargs):
        msg, kwargs = super().process(msg, kwargs)
        kwargs['extra']['taskname'] = get_current_task_name()
        return msg, kwargs

    def _get_connection_logger_cls(self) -> Type[BaseLogger]:
        if self._get_child_logger('stats').isEnabledFor(logging.INFO):
            return ConnectionLoggerStats
        return ConnectionLogger

    def _get_child_logger(self, name):
        child_name = f"{self.name}.{name}"
        return logging.getLogger(child_name)

    def get_connection_logger(self, name: str = 'connection', **kwargs) -> Any:
        return self.get_child(name=name, cls=self.connection_logger_cls, **kwargs)

    def get_child(self, name: str = '', cls: Type = None, **kwargs) -> Any:
        logger_name = f"{self.logger_name}.{name}"
        return self._get_logger(name=logger_name, cls=cls, **kwargs)

    def get_sibling(self, *args, name: str = '', **kwargs) -> Any:
        name = f'{self.logger.parent.name}.{name}'
        return self._get_logger(*args, name=name, **kwargs)

    def _get_logger(self, name: str = '', cls: Type[BaseLogger] = None, extra: Dict[str, Any] = None, **kwargs) -> Any:
        cls = cls or self.__class__
        extra = ChainMap(extra or {}, self.extra)
        return cls(name, extra=extra, **kwargs)

    def log_num_connections(self, action: str, parent_id: int):
        self.debug('Connection %s. There %s now %s.', action,
                          p.plural_verb('is', p.num(connections_manager.num_connections(parent_id))),
                          p.no('active connection'))

    def _set_closing(self) -> None:
        self._is_closing = True


@dataclass
class ConnectionLogger(Logger):

    def __init__(self, *args, is_receiver: bool = False, extra: Dict[str, Any] = None, **kwargs):
        extra = self.get_extra(extra or {}, is_receiver)
        super().__init__(*args, extra=extra, **kwargs)
        self._raw_received_logger = self.get_sibling(name='raw_received', cls=Logger)
        self._raw_sent_logger = self.get_sibling(name='raw_sent', cls=Logger)
        self._data_received_logger = self.get_sibling(name='data_received', cls=Logger)
        self._data_sent_logger = self.get_sibling(name='data_sent', cls=Logger)

    @staticmethod
    def get_extra(extra: Dict[str, Any], is_receiver: bool):
        extra = extra.copy()
        if 'sock' in extra:
            #Socket based connections
            extra.update({
                'server': extra.get('sock', '') if is_receiver else extra.get('peer', ''),
                'client': extra.get('peer', '') if is_receiver else extra.get('sock', '')
            })
        else:
            #Pipe based connections
            extra.update({
                'server': extra.get('addr', ''),
                'client': extra.get('handle', '')
            })
        return extra

    @property
    def connection_type(self) -> str:
        return self.extra['protocol_name']

    @property
    def client(self) -> str:
        return self.extra['client']

    @property
    def server(self) -> str:
        return self.extra['server']

    @property
    def peer(self) -> str:
        return self.extra['peer']

    def _raw_received(self, data: AnyStr, *args, **kwargs) -> None:
        self._raw_received_logger.debug(data, *args, **kwargs)

    def _raw_sent(self, data: AnyStr, *args, **kwargs) -> None:
        self._raw_sent_logger.debug(data, *args, **kwargs)

    def _data_received(self, msg_obj: MessageObjectType, *args, msg: str = '', **kwargs) -> None:
        extra = ChainMap({'data': msg_obj, 'direction': "RECEIVED"}, self.extra)
        self._data_received_logger.debug(msg, *args, extra=extra, **kwargs)

    def _data_sent(self, msg_obj: MessageObjectType, *args, msg: str = '', **kwargs) -> None:
        extra = ChainMap({'data': msg_obj, 'direction': "SENT"}, self.extra)
        self._data_sent_logger.debug(msg, *args, extra=extra, **kwargs)

    def new_connection(self) -> None:
        self.info('New %s connection from %s to %s', self.connection_type, self.client, self.server)

    def _on_msg_decoded(self, msg_obj: MessageObjectType) -> None:
        self._data_received(msg_obj)

    def _log_decoded_msgs(self, msgs: Iterable[MessageObjectType]) -> None:
        for msg_obj in msgs:
            self._on_msg_decoded(msg_obj)

    def on_buffer_received(self, data: AnyStr) -> None:
        self.debug("Received msg from %s", self.peer)
        self._raw_received(data)

    def log_msgs(self, msgs: Iterable[MessageObjectType]) -> None:
        self.logger.debug('Buffer contains %s', p.no('message', msgs))
        self.logger.log_decoded_msgs(msgs)

    def on_sending_decoded_msg(self, msg_obj: MessageObjectType) -> None:
        self._data_sent(msg_obj)

    def on_sending_encoded_msg(self, data: AnyStr) -> None:
        self.debug("Sending message to %s", self.peer)
        self._raw_sent(data)

    def on_msg_sent(self, data: AnyStr) -> None:
        self.debug('Message sent')

    def on_msg_processed(self, msg: int) -> None:
        pass

    def connection_finished(self, exc: Optional[BaseException] = None) -> None:
        self.manage_error(exc)
        self.info('%s connection from %s to %s has been closed', self.connection_type, self.client, self.server)


@dataclass
class StatsTracker:
    datefmt: str = '%Y-%M-%d %H:%M:%S'
    start: LoggingDatetime = field(default=None, init=False)
    end: LoggingDatetime = field(default=None, init=False)
    sent: BytesSize = field(default_factory=BytesSize, init=False)
    received: BytesSize = field(default_factory=BytesSize, init=False)
    processed: BytesSize = field(default_factory=BytesSize, init=False)
    msgs: MsgsCount = field(default_factory=MsgsCount, init=False)

    attrs = ('start', 'end', 'msgs', 'sent', 'received', 'processed',
             'processing_rate', 'receive_rate', 'interval', 'average_buffer', 'average_sent')

    def __post_init__(self):
        self.start = LoggingDatetime(datefmt=self.datefmt)

    @property
    def processing_rate(self) -> float:
        return self.processed.average(self.msgs.processing_time)

    @property
    def receive_rate(self) -> float:
        return self.received.average(self.msgs.receive_interval)

    @property
    def interval(self) -> LoggingTimeDelta:
        return LoggingTimeDelta(self.start, self.end)

    @property
    def average_buffer(self) -> float:
        return self.received.average(self.msgs.received)

    @property
    def average_sent(self) -> float:
        return self.sent.average(self.msgs.sent)

    def __iter__(self) -> Generator[Any, None, None]:
        yield from self.attrs

    def __getitem__(self, item: Any) -> Any:
        return getattr(self, item)

    def on_buffer_received(self, msg: AnyStr) -> None:
        if not self.msgs.first_received:
            self.msgs.first_received = LoggingDatetime(self.datefmt)
        self.msgs.last_received = LoggingDatetime(self.datefmt)
        self.msgs.received += 1
        self.received += len(msg)

    def on_msg_processed(self, num_bytes: int) -> None:
        self.msgs.last_processed = LoggingDatetime(self.datefmt)
        self.msgs.processed += 1
        self.processed += num_bytes

    def on_msg_sent(self, msg: AnyStr) -> None:
        if not self.msgs.first_sent:
            self.msgs.first_sent = datetime.now()
        self.msgs.sent += 1
        self.sent += len(msg)

    def end_interval(self) -> None:
        self.end = LoggingDatetime(self.datefmt)


@dataclass
class StatsLogger(Logger):
    _first = True
    _stats: StatsTracker = None
    _scheduler: TaskScheduler = field(init=False, default_factory=TaskScheduler)
    interval: Union[int, float] = 0
    fixed_start_time: bool = True
    stats_cls = StatsTracker
    _total_received = 0
    _total_processed = 0

    def __init__(self, logger_name: str, extra: dict, *args, interval: int = 0, fixed_start_time: bool = True, **kwargs):
        self._scheduler = TaskScheduler()
        super().__init__(logger_name, *args, extra=extra, **kwargs)
        self._stats = self.stats_cls(datefmt=self.datefmt)
        if interval:
            self._scheduler.call_cb_periodic(interval, self.periodic_log, fixed_start_time=fixed_start_time)

    def process(self, msg, kwargs):
        self._stats.end_interval()
        msg, kwargs = super().process(msg, kwargs)
        kwargs['extra'].update({k: self._stats[k] for k in self._stats})
        return msg, kwargs

    def reset(self):
        self._stats = self.stats_cls(datefmt=self.datefmt)

    def stats(self, tag: str) -> None:
        self._first = False
        self._total_received += self._stats.received
        self._total_processed += self._stats.processed
        self.info(tag)
        self.reset()

    def periodic_log(self, first: bool = True) -> None:
        self.stats("INTERVAL")

    def _check_last_message_processed(self) -> None:
        if (self._total_received + self._stats.received) == (self._total_processed + self._stats.processed):
            self._stats.end_interval()
            tag = 'ALL' if self._first else 'END'
            self.stats(tag)

    def finish(self):
        self._set_closing()
        self._check_last_message_processed()
        self._scheduler.close_nowait()

    def on_msg_processed(self, num_bytes: int):
        self._stats.on_msg_processed(num_bytes)
        if self._is_closing:
            self._check_last_message_processed()

    def __getattr__(self, item):
        if self._stats:
            return getattr(self._stats, item)


@dataclass
class ConnectionLoggerStats(ConnectionLogger):
    stats_cls = StatsLogger

    def __init__(self, *args, **kwargs):
        self._stats_logger = self._get_stats_logger()
        super().__init__(*args, **kwargs)

    def _get_stats_logger(self) -> StatsLogger:
        return self.get_sibling('stats', cls=self.stats_cls)

    def on_buffer_received(self, msg: AnyStr) -> None:
        super().on_buffer_received(msg)
        self._stats_logger.on_buffer_received(msg)

    def on_msg_processed(self, num_bytes: int) -> None:
        super().on_msg_processed(num_bytes)
        self._stats_logger.on_msg_processed(num_bytes)

    def on_msg_sent(self, msg: AnyStr) -> None:
        super().on_msg_sent(msg)
        self._stats_logger.on_msg_sent(msg)

    def connection_finished(self, exc: Optional[Exception] = None) -> None:
        super().connection_finished(exc=exc)
        self._stats_logger.finish()


def connection_logger_receiver() -> ConnectionLoggerType:
    return ConnectionLogger('receiver.connection', is_receiver=True)


def connection_logger_sender() -> ConnectionLoggerType:
    return ConnectionLogger('sender.connection', is_receiver=False)
