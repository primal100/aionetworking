from __future__ import annotations
from abc import ABC, abstractmethod
import binascii
import logging
from datetime import datetime
from dataclasses import dataclass, field

#from pydantic import ValidationError

from lib.compatibility import get_current_task_name
from lib.utils import dataclass_getstate, dataclass_setstate
from lib.utils import log_exception
from lib.utils_logging import LoggingDatetime, LoggingTimeDelta, BytesSize, MsgsCount, p
from lib.wrappers.schedulers import TaskScheduler

from typing import Type, Optional, Dict, AnyStr, Generator, Any, Union
from lib.formats.types import MessageObjectType
from .types import ConnectionLoggerType


class BaseLogger(logging.LoggerAdapter, ABC):

    def update_extra(self, **kwargs):
        self.extra.update(**kwargs)

    def manage_error(self, exc: BaseException) -> None:
        if exc:
            self.error(log_exception(exc))

    def manage_critical_error(self, exc: BaseException) -> None:
        if exc:
            self.critical(log_exception(exc))

    @abstractmethod
    def _get_connection_logger_cls(self) -> Type: ...

    @abstractmethod
    def get_connection_logger(self, name: str = 'connection', **kwargs): ...

    @abstractmethod
    def get_child(self, name: str, cls: Type = None, **kwargs) -> BaseLogger: ...

    @abstractmethod
    def get_sibling(self, name: str, **kwargs) -> BaseLogger: ...

    @abstractmethod
    def _get_logger(self, name: str = '', cls: Type[BaseLogger] = None, extra: Dict[str, Any] = None, **kwargs) -> Any: ...

    async def wait_closed(self): ...


@dataclass
class Logger(BaseLogger):
    logger_name: str
    datefmt: str = '%Y-%M-%d %H:%M:%S'
    extra: dict = None
    stats_interval: Union[float, int] = 0
    stats_fixed_start_time: bool = True
    _is_closing: bool = field(default=False, init=False)

    def __init__(self, logger_name: str, datefmt: str = '%Y-%M-%d %H:%M:%S', extra: Dict = None,
                 stats_interval: Optional[Union[int, float]] = 0, stats_fixed_start_time: bool = True):
        self.logger_name = logger_name
        self.datefmt = datefmt
        self.stats_interval = stats_interval
        self.stats_fixed_start_time = stats_fixed_start_time
        logger = logging.getLogger(logger_name)
        super().__init__(logger, extra or {})

    def __getstate__(self):
        state = dataclass_getstate(self)
        if self._is_closing:
            state['_is_closing'] = self._is_closing
        return state

    def __setstate__(self, state):
        self._is_closing = state.pop('_is_closing', self._is_closing)
        dataclass_setstate(self, state)

    def process(self, msg, kwargs):
        msg, kwargs = super().process(msg, kwargs)
        kwargs['extra'] = kwargs['extra'].copy()
        kwargs['extra']['taskname'] = get_current_task_name()
        kwargs['extra'].update(kwargs.pop('detail', {}))
        return msg, kwargs

    def _get_connection_logger_cls(self) -> Type[BaseLogger]:
        if self._get_child_logger('stats').isEnabledFor(logging.INFO):
            return ConnectionLoggerStats
        return ConnectionLogger

    def _get_child_logger(self, name):
        child_name = f"{self.name}.{name}"
        return logging.getLogger(child_name)

    def get_connection_logger(self, name: str = 'connection', **kwargs) -> Any:
        connection_logger_cls = self._get_connection_logger_cls()
        return self.get_child(name, cls=connection_logger_cls, stats_interval=self.stats_interval,
                              stats_fixed_start_time=self.stats_fixed_start_time, **kwargs)

    def get_child(self, name: str, cls: Type = None, **kwargs) -> Any:
        logger_name = f"{self.logger_name}.{name}"
        return self._get_logger(name=logger_name, cls=cls, **kwargs)

    def get_sibling(self, name: str, *args, **kwargs) -> Any:
        name = f'{self.logger.parent.name}.{name}'
        return self._get_logger(*args, name=name, **kwargs)

    def _get_logger(self, name: str = '', cls: Type[BaseLogger] = None, extra: Dict[str, Any] = None, **kwargs) -> Any:
        cls = cls or self.__class__
        extra = extra or {}
        extra.update(self.extra)
        return cls(name, extra=extra, **kwargs)

    def log_num_connections(self, action: str, num_connections: int):
        if self.isEnabledFor(logging.DEBUG):
            self.log(logging.DEBUG, 'Connection %s. There %s now %s.', action,
                        p.plural_verb('is', p.num(num_connections)),
                        p.no('active connection'))

    def _set_closing(self) -> None:
        self._is_closing = True


@dataclass
class ConnectionLogger(Logger):

    def __init__(self, *args, extra: Dict[str, Any] = None, **kwargs):
        extra = extra or {}
        super().__init__(*args, extra=extra, **kwargs)
        self._raw_received_logger = self.get_sibling('raw_received', cls=Logger)
        self._raw_sent_logger = self.get_sibling('raw_sent', cls=Logger)
        self._data_received_logger = self.get_sibling('data_received', cls=Logger)
        self._data_sent_logger = self.get_sibling('data_sent', cls=Logger)

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

    @staticmethod
    def _convert_raw_to_hex(data: AnyStr):
        if isinstance(data, bytes):
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return binascii.hexlify(data).decode('utf-8')
        return data

    def _raw_received(self, data: AnyStr, *args, **kwargs) -> None:
        msg = self._convert_raw_to_hex(data)
        self._raw_received_logger.debug(msg, *args, **kwargs)

    def _raw_sent(self, data: AnyStr, *args, **kwargs) -> None:
        msg = self._convert_raw_to_hex(data)
        self._raw_sent_logger.debug(msg, *args, **kwargs)

    def _data_received(self, msg_obj: MessageObjectType, *args, msg: str = '', **kwargs) -> None:
        self._data_received_logger.debug(msg, *args, detail={'data': msg_obj, 'direction': 'RECEIVED'}, **kwargs)

    def _data_sent(self, msg_obj: MessageObjectType, *args, msg: str = '', **kwargs) -> None:
        self._data_received_logger.debug(msg, *args, detail={'data': msg_obj, 'direction': 'SENT'}, **kwargs)

    def on_msg_decoded(self, msg_obj: MessageObjectType) -> None:
        self._data_received(msg_obj)

    def new_connection(self) -> None:
        self.info('New %s connection from %s to %s', self.connection_type, self.client, self.server)

    def on_buffer_received(self, data: AnyStr) -> None:
        self.debug("Received message from %s", self.peer)
        self._raw_received(data)

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
    largest_buffer: BytesSize = field(default_factory=BytesSize, init=False)
    msgs: MsgsCount = field(default_factory=MsgsCount, init=False)

    attrs = ('start', 'end', 'msgs', 'sent', 'received', 'processed', 'largest_buffer',
             'processing_rate', 'receive_rate', 'interval', 'average_buffer_size', 'average_sent', 'msgs_per_buffer')

    def __post_init__(self):
        self.start = LoggingDatetime(datefmt=self.datefmt)

    @property
    def processing_rate(self) -> float:
        return self.processed / (self.msgs.processing_time or 1)

    @property
    def receive_rate(self) -> float:
        return self.received / (self.msgs.receive_interval or 1)

    @property
    def msgs_per_buffer(self) -> float:
        return self.msgs.processed / (self.msgs.received or 1)

    @property
    def interval(self) -> LoggingTimeDelta:
        return LoggingTimeDelta(self.start, self.end)

    @property
    def average_buffer_size(self) -> float:
        return self.received / ( self.msgs.received or 1)

    @property
    def average_sent(self) -> float:
        return self.sent / (self.msgs.sent or 1)

    def __iter__(self) -> Generator[Any, None, None]:
        yield from self.attrs

    def __getitem__(self, item: Any) -> Any:
        return getattr(self, item)

    def on_buffer_received(self, msg: AnyStr) -> None:
        if not self.msgs.first_received:
            self.msgs.first_received = LoggingDatetime(self.datefmt)
        self.msgs.last_received = LoggingDatetime(self.datefmt)
        self.msgs.received += 1
        size = len(msg)
        self.received += size
        if size > self.largest_buffer:
            self.largest_buffer = BytesSize(size)

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
    _stats: StatsTracker = field(default=None, init=False, compare=False)
    _scheduler: TaskScheduler = field(init=False, default_factory=TaskScheduler, compare=False)
    stats_cls = StatsTracker
    _total_received = BytesSize()
    _total_processed = BytesSize()

    def __init__(self, logger_name: str, extra: dict, *args, **kwargs):
        self._scheduler = TaskScheduler()
        super().__init__(logger_name, *args, extra=extra, **kwargs)
        self._stats = self.stats_cls(datefmt=self.datefmt)
        self.info('\n')
        if self.stats_interval:
            self._scheduler.call_cb_periodic(self.stats_interval, self.periodic_log,
                                             fixed_start_time=self.stats_fixed_start_time)

    def process(self, msg, kwargs):
        self._stats.end_interval()
        msg, kwargs = super().process(msg, kwargs)
        kwargs['extra'].update({k: self._stats[k] for k in self._stats})
        return msg, kwargs

    def reset(self):
        self._stats = self.stats_cls(datefmt=self.datefmt)

    def stats(self, tag: str) -> None:
        self._first = False
        self.info(tag)
        self._total_received += self._stats.received
        self._total_processed += self._stats.processed
        self.reset()

    def periodic_log(self, first: bool = True) -> None:
        self.stats("INTERVAL")

    def _check_last_message_processed(self) -> None:
        if (self._total_received + self._stats.received) == (self._total_processed + self._stats.processed):
            self._stats.end_interval()
            tag = 'ALL' if self._first else 'END'
            self.stats(tag)

    def connection_finished(self):
        self._set_closing()
        self._check_last_message_processed()
        self._scheduler.close_nowait()

    async def wait_closed(self):
        await self._scheduler.close()

    def on_msg_processed(self, num_bytes: int):
        if num_bytes > 100:
            pass
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
        super().__init__(*args, **kwargs)
        self._stats_logger = self._get_stats_logger()

    def _get_stats_logger(self) -> StatsLogger:
        return self.get_sibling('stats', cls=self.stats_cls, stats_interval=self.stats_interval,
                                stats_fixed_start_time=self.stats_fixed_start_time)

    def on_buffer_received(self, msg: AnyStr) -> None:
        super().on_buffer_received(msg)
        self._stats_logger.on_buffer_received(msg)

    def on_msg_processed(self, num_bytes: int) -> None:
        super().on_msg_processed(num_bytes)
        self._stats_logger.on_msg_processed(num_bytes)

    def on_msg_sent(self, msg: AnyStr) -> None:
        super().on_msg_sent(msg)
        self._stats_logger.on_msg_sent(msg)

    def connection_finished(self, exc: Optional[BaseException] = None) -> None:
        super().connection_finished(exc=exc)
        self._stats_logger.connection_finished()

    async def wait_closed(self):
        await self._stats_logger.wait_closed()


def connection_logger_receiver() -> ConnectionLoggerType:
    return ConnectionLogger('receiver.connection')


def connection_logger_sender() -> ConnectionLoggerType:
    return ConnectionLogger('sender.connection')
