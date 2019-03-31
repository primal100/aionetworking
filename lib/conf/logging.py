import logging
from functools import partial
from collections import ChainMap
from datetime import datetime
from dataclasses import field

from pydantic.dataclasses import dataclass

from lib.utils import log_exception
from lib.utils_logging import LoggingDatetime, LoggingTimeDelta, BytesSize, MsgsCount
from lib.wrappers.periodic import call_cb_periodic


from typing import TYPE_CHECKING, Type, Optional, MutableMapping, Union, NoReturn, AnyStr, Iterable, Generator, Any
if TYPE_CHECKING:
    from lib.formats.base import BaseMessageObject
else:
    BaseMessageObject = None


class _Logger(BaseConfigurable, logging.LoggerAdapter):
    pass


class Logger(_Logger):
    logger = None
    _instances = {}
    logger_name: str = ''
    datefmt: str = '%Y-%M-%d %H:%M:%S'
    extra: dict = field(default_factory=dict, metadata={'configurable': False})

    @classmethod
    def validate(cls, logger, *args, **kwargs) -> str:
        if isinstance(logger, cls):
            instance = logger
            if not instance.logger_name in cls._instances:
                cls._instances[instance.logger_name] = instance
                return instance
        else:
            if logger in cls._instances:
                return cls._instances[logger]
            instance = cls(logger)
            cls._instances[logger] = instance
            return instance

    def __post_init__(self):
        logger = logging.getLogger(self.logger_name)
        super().__init__(logger, self.extra)
        self.connection_logger_cls = self.get_connection_logger_cls()
        super().__post_init__()

    def get_connection_logger_cls(self) -> Type[_Logger]:
        if self.get_child('stats').isEnabledFor(logging.INFO):
            return ConnectionLoggerStats
        return ConnectionLogger

    def manage_error(self, exc: Exception) -> NoReturn:
        if exc:
            self.error(log_exception(exc))

    def get_connection_logger(self, *args, name: str = 'connection', **kwargs) -> _Logger:
        return self.get_child(*args, name=name, cls=self.connection_logger_cls, **kwargs)

    def get_child(self, *args, name: str = '', **kwargs) -> _Logger:
        logger_name = f"{self.logger_name}.{name}"
        return self.get_logger(*args, name=logger_name, **kwargs)

    def get_sibling(self, *args, name: str = '', **kwargs) -> _Logger:
        name = f'{self.logger.parent.name}.{name}'
        return self.get_logger(*args, name=name, **kwargs)

    def get_logger(self, name: str = '', cls: Type[_Logger]=None, context: MutableMapping = None, **kwargs) -> _Logger:
        cls = cls or Logger
        context = context or {}
        extra = ChainMap(context, self.extra)
        return cls(name, extra, **kwargs)


class ConnectionLogger(Logger):
    _is_closing: bool = False

    def __post_init__(self):
        super().__post_init__()
        self._raw_received_logger = self.logger.get_sibling('raw_received')
        self._raw_sent_logger = self.logger.get_sibling('raw_sent')
        self._data_received_logger = self.logger.get_sibling('data_received')
        self._data_sent_logger = self.logger.get_sibling('data_sent')

    def msg_logger(self, msg: BaseMessageObject) -> _Logger:
        return self.get_child('msg', context={'msg_obj': msg})

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
    def alias(self) -> str:
        return self.extra['alias']

    @property
    def peer(self) -> str:
        return self.extra['peer']

    def _raw_received(self, data: AnyStr, *args, **kwargs) -> NoReturn:
        self._raw_received_logger.debug(data, *args, **kwargs)

    def _raw_sent(self, data: AnyStr, *args, **kwargs) -> NoReturn:
        self._raw_sent_logger.debug(data, *args, **kwargs)

    def _data_received(self, msg_obj: BaseMessageObject, *args, msg: str = '', **kwargs) -> NoReturn:
        extra = ChainMap({'data': msg_obj}, self.extra)
        self._data_received_logger.debug(msg, *args, extra=extra, **kwargs)

    def _data_sent(self, msg_obj: BaseMessageObject, *args, msg: str = '', **kwargs) -> NoReturn:
        extra = ChainMap({'data': msg_obj}, self.extra)
        self._data_sent_logger.debug(msg, *args, extra=extra, **kwargs)

    def new_connection(self) -> NoReturn:
        self.info('New %s connection from %s to %s', self.connection_type, self.client, self.server)

    def on_buffer_received(self, data: AnyStr) -> NoReturn:
        self.debug("Received msg from %s", self.alias)
        self._raw_received(data)

    def on_msg_decoded(self, msg_obj: BaseMessageObject) -> NoReturn:
        self._data_received(msg_obj)

    def log_decoded_msgs(self, msgs: Iterable[BaseMessageObject]) -> NoReturn:
        for msg_obj in msgs:
            self.on_msg_decoded(msg_obj)

    def on_sending_decoded_msg(self, msg_obj: BaseMessageObject) -> NoReturn:
        self._data_sent(msg_obj)

    def on_sending_encoded_msg(self, data: AnyStr) -> NoReturn:
        self.debug("Sending message to %s", self.peer)
        self._raw_sent(data)

    def on_msg_sent(self, data: AnyStr) -> NoReturn:
        self.debug('Message sent')

    def on_msg_processed(self, msg: int) -> NoReturn:
        pass

    def connection_finished(self, exc: Optional[Exception] = None) -> NoReturn:
        self.manage_error(exc)
        self.info('%s connection from %s to %s has been closed', self.connection_type, self.client, self.server)

    def set_closing(self)-> NoReturn:
        self._is_closing = True


class _StatsTracker(dict):
    pass


class StatsTracker(_StatsTracker):
    attrs = ('start', 'end', 'msgs', 'sent', 'received', 'processed',
             'processing_rate', 'receive_rate', 'interval', 'average_buffer', 'average_sent')

    def reset(self) -> _StatsTracker:
        return self.__class__(self.properties, self.datefmt)

    def __init__(self, properties: MutableMapping, datefmt: str ="%Y-%M-%d %H:%M:%S"):
        super().__init__()
        self.datefmt = datefmt
        self.properties = properties
        self.start = LoggingDatetime(datefmt=datefmt)
        self.msgs = MsgsCount()
        self.sent = BytesSize(0)
        self.received = BytesSize(0)
        self.processed = BytesSize(0)
        self.test = BytesSize(10)
        self.end = None

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
        for item in tuple(self.properties) + self.attrs:
            yield item

    def __getitem__(self, item: Any) -> Any:
        if item in self.properties:
            return self.properties[item]
        if item in self.attrs:
            return getattr(self, item)

    def on_buffer_received(self, msg: AnyStr) -> NoReturn:
        if not self.msgs.first_received:
            self.msgs.first_received = LoggingDatetime(self.datefmt)
        self.msgs.last_received = LoggingDatetime(self.datefmt)
        self.msgs.received += 1
        self.received += len(msg)

    def on_msg_processed(self, num_bytes: int) -> NoReturn:
        self.msgs.last_processed = datetime.now()
        self.msgs.processed += 1
        self.processed += num_bytes

    def on_msg_sent(self, msg: AnyStr) -> NoReturn:
        if not self.msgs.first_sent:
            self.msgs.first_message_sent = datetime.now()
        self.msgs.sent += 1
        self.sent += len(msg)

    def finish(self) -> NoReturn:
        self.end = LoggingDatetime(self.datefmt)


class StatsLogger(Logger):
    stats_cls = StatsTracker

    def __post_init__(self):
        self.extra = self.stats_cls(self.extra, datefmt=self.datefmt)
        super().__post_init__()

    def reset(self):
        self.extra = self.extra.reset()


class ConnectionLoggerStats(ConnectionLogger):
    _total_received = 0
    _total_processed = 0
    _first = True
    stats_cls = StatsLogger
    interval: int = 0

    def __post_init__(self):
        self._stats_logger = self.logger.get_child('stats', cls=self.stats_cls)
        super().__post_init__()
        if self.interval:
            call_cb_periodic(self.interval, self.periodic_log, fixed_start_time=True)

    def periodic_log(self, first: bool) -> NoReturn:
        self.extra.end_time = datetime.now()
        tag = 'NEW' if first else 'INTERVAL'
        self.stats(tag)
        self._first = False
        self._total_received += self.extra.msgs.received
        self._total_processed += self.extra.msgs.processed
        self._stats_logger.reset()

    def stats(self, tag: str) -> NoReturn:
        self._stats_logger.info(tag)

    def on_buffer_received(self, msg: AnyStr) -> NoReturn:
        super().on_buffer_received(msg)
        self.extra.on_buffer_received(msg)

    def on_msg_processed(self, num_bytes: int) -> NoReturn:
        super().on_msg_processed(num_bytes)
        self.extra.on_msg_processed(num_bytes)
        if self._is_closing:
            self.check_last_message_processed()

    def on_msg_sent(self, msg: AnyStr) -> NoReturn:
        super().on_msg_sent(msg)
        self.extra.on_msg_sent(msg)

    def check_last_message_processed(self) -> NoReturn:
        if (self._total_received + self.extra.msgs.received) == (self._total_processed + self.extra.msgs.processed):
            self.extra.finish()
            tag = 'ALL' if self._first else 'END'
            self.stats(tag)

    def connection_finished(self, exc: Optional[Exception] = None) -> NoReturn:
        super().connection_finished(exc=exc)
        self.set_closing()
        self.check_last_message_processed()
