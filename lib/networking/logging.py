import logging
from datetime import datetime
from functools import partial

from lib.utils import  log_exception
from lib.wrappers.periodic import call_cb_periodic


class SimpleConnectionLogger(logging.LoggerAdapter):
    def manage_error(self, exc):
        if exc:
            self.error(log_exception(exc))


class ConnectionLogger(SimpleConnectionLogger):...


measures = {
    'byte': 1,
    'kb': 1024,
    'mb': 1048576,
    'gb': 1073741824
}


class StatsTracker(dict):
    default_attrs = ('start_time', 'end_time', 'received_msgs', 'received_kb','processed_kb', 'processing_rate_kb')
    sent_msgs: int = 0
    sent_bytes: int = 0
    received_msgs: int = 0
    received_bytes: int = 0
    processed_msgs: int = 0
    processed_bytes: int = 0
    start_time: datetime = None
    end_time: datetime = None
    first_message_received: datetime = None
    first_message_sent: datetime = None
    last_message_received: datetime = None
    last_message_processed: datetime = None

    @property
    def percent_processed(self):
        return self.processed_msgs / self.received_msgs

    @property
    def processing_rate_bytes(self):
        return self.processed_bytes / self.processing_time

    @property
    def receive_rate_bytes(self):
        return self.received_bytes / (self.last_message_received - self.last_message_processed).total_seconds()

    @property
    def buffer_processing_rate(self):
        return self.processed_msgs / self._processing_time

    @property
    def buffer_receive_rate(self):
        return self.received_msgs / (self.last_message_received - self.last_message_processed).total_seconds()

    @property
    def _processing_time(self):
        return (self.last_message_processed - self.first_message_received).total_seconds()

    @property
    def processing_time(self):
        return self._processing_time / self._seconds_divice_by

    @property
    def _interval_time(self):
        return (self.end_time - self.start_time).total_seconds()

    @property
    def interval_time(self):
        return self._interval_time / self._seconds_divice_by

    @property
    def average_buffer_bytes(self):
        return self.received_bytes / self.received_msgs

    @property
    def average_sent_bytes(self):
        return self.sent_bytes / self.sent_msgs

    def __iter__(self):
        for item in  super().__iter__():
            yield item
        for attr in self.attrs:
            yield attr

    def __getitem__(self, item):
        if "__" in item:
            attr, measure = item.split('__')
            if measure == 'time':
                dt = getattr(self, "%s_time" % attr)
                return dt.strftime(self._time_strf)
            else:
                num_bytes = getattr(self, "%s_bytes" % attr)
                return num_bytes / measures[measure]
        if item in self.attrs:
            return getattr(self, item, None)
        return super().__getitem__(item)

    def __init__(self, properties, attrs, time_strf=None, seconds_divide_by=None):
        super().__init__(properties)
        self._time_strf = time_strf
        self._seconds_divice_by = seconds_divide_by
        self.properties = properties
        self.attrs = attrs or self.default_attrs
        self.start_time = datetime.now()


class NoStatsLogger(logging.LoggerAdapter):

    def connection_started(self): ...

    def on_msg_received(self, msg): ...

    def on_msg_processed(self, num_bytes): ...

    def on_msg_sent(self, msg): ...

    def connection_finished(self): ...


class StatsLogger(NoStatsLogger):
    _total_received: int = 0
    _total_processed: int = 0
    _first: bool = True
    configs = {}
    loggers = {}
    configurable = {
        'interval': int,
        'attrs': tuple,
        'timestrf': str,
        'secondsdivideby': int
    }

    @classmethod
    def with_config(cls, logger, cp=None, **kwargs):
        stats_logger = logging.getLogger(f'{logger.name}.stats')
        if stats_logger.isEnabledFor(logging.INFO):
            handler_name = "handler_%s_stats" % logger.name
            config = cp.section_as_dict(handler_name, **cls.configurable)
            logger.debug(f'Found config for {logger.name} stats: {config}')
            config.update(**kwargs)
            return partial(cls, stats_logger, **config)
        return partial(cls, NoStatsLogger, stats_logger)

    @classmethod
    def from_config(cls, logger_name, *args, cp=None, **kwargs):
        if logger_name in cls.loggers:
            logger = cls.loggers[logger_name]
            config = cls.loggers[logger_name]
        else:
            logger = logging.getLogger("%s.stats" % logger_name)
            handler_name = "%s_stats" % logger_name
            cls.loggers[logger_name] = logger
            if logger.isEnabledFor(logging.INFO):
                from lib import settings
                cp = cp or settings.CONFIG
                config = cp.section_as_dict('handler_%s' % handler_name, **cls.configurable)
                base_logger = logging.getLogger(logger_name)
                base_logger.debug('Found config for %s stats', logger_name)
                cls.configs[logger_name] = config
            else:
                config = cls.configs[logger_name] = {}
        if logger.isEnabledFor(logging.INFO):
            if kwargs:
                kwargs.update(config)
                config = kwargs
            return cls(logger, *args, **config)
        return NoStatsLogger(logger, {})

    def __init__(self, logger, extra, transport, attrs=(), interval=0, timestrf=None, secondsdivideby=1):
        stats = StatsTracker(extra, attrs, time_strf=timestrf, seconds_divide_by=secondsdivideby)
        super().__init__(logger, stats)
        self.transport = transport
        self.connection_started()
        if interval:
            call_cb_periodic(interval, self.periodic_log, fixed_start_time=True)

    def periodic_log(self, first):
        self.extra.end_time = datetime.now()
        tag = 'NEW' if first else 'INTERVAL'
        self.info(tag)
        self._first = False
        self._total_received += self.extra.received_msgs
        self._total_processed += self.extra.processed_msgs
        self.extra = StatsTracker(self.extra.properties, self.extra.attrs)

    def connection_started(self):
        self.extra.start_time = datetime.now()

    def on_msg_received(self, msg):
        if not self.extra.first_message_received:
            self.extra.first_message_received = datetime.now()
        self.extra.last_message_received = datetime.now()
        self.extra.received_msgs += 1
        self.extra.received_bytes += len(msg)

    def on_msg_processed(self, num_bytes):
        self.extra.last_message_processed = datetime.now()
        self.extra.processed_msgs += 1
        self.extra.processed_bytes += num_bytes
        if self.transport.is_closing():
            self.check_last_message_processed()

    def on_msg_sent(self, msg):
        if not self.extra.first_message_sent:
            self.extra.first_message_sent = datetime.now()
        self.extra.sent_msgs += 1
        self.extra.sent_bytes += len(msg)

    def check_last_message_processed(self):
        if (self._total_received + self.extra.received_msgs) == (self._total_processed + self.extra.processed_msgs):
            self.extra.end_time = datetime.now()
            tag = 'ALL' if self._first else 'END'
            self.info(tag)

    def connection_finished(self):
        self.extra.end_time = datetime.now()
        self.check_last_message_processed()
