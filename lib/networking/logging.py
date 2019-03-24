import logging
from datetime import datetime
from functools import partial

from lib.utils_logging import LoggingDatetime, LoggingTimeDelta, BytesSize, MsgsCount
from lib.utils import log_exception
from lib.wrappers.periodic import call_cb_periodic


class SimpleConnectionLogger(logging.LoggerAdapter):
    def manage_error(self, exc):
        if exc:
            self.error(log_exception(exc))


class ConnectionLogger(SimpleConnectionLogger):...


class StatsTracker:
    attrs = ('start', 'end', 'msgs', 'sent', 'received', 'processed',
             'processing_rate', 'receive_rate', 'interval', 'average_buffer', 'average_sent')

    def reset(self):
        return self.__class__(self.properties, self.datefmt)

    def __init__(self, properties, datefmt="%Y-%M-%d %H:%M:%S"):
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
    def processing_rate(self):
        return self.processed.average(self.msgs.processing_time)

    @property
    def receive_rate(self):
        return self.received.average(self.msgs.receive_interval)

    @property
    def interval(self):
        return LoggingTimeDelta(self.start, self.end)

    @property
    def average_buffer(self):
        return self.received.average(self.msgs.received)

    @property
    def average_sent(self):
        return self.sent.average(self.msgs.sent)

    def __iter__(self):
        for item in tuple(self.properties) + self.attrs:
            yield item

    def __getitem__(self, item):
        if item in self.properties:
            return self.properties[item]
        if item in self.attrs:
            return getattr(self, item)

    def on_msg_received(self, msg):
        if not self.msgs.first_received:
            self.msgs.first_received = LoggingDatetime(self.datefmt)
        self.msgs.last_received = LoggingDatetime(self.datefmt)
        self.msgs.received += 1
        self.received += len(msg)

    def on_msg_processed(self, num_bytes):
        self.msgs.last_processed = datetime.now()
        self.msgs.processed += 1
        self.processed += num_bytes

    def on_msg_sent(self, msg):
        if not self.msgs.first_sent:
            self.msgs.first_message_sent = datetime.now()
        self.msgs.sent += 1
        self.sent += len(msg)

    def finish(self):
        self.end = LoggingDatetime(self.datefmt)


class NoStatsLogger(logging.LoggerAdapter):
    _is_closing: bool = False

    def connection_started(self): ...

    def on_msg_received(self, msg): ...

    def on_msg_processed(self, num_bytes): ...

    def on_msg_sent(self, msg): ...

    def connection_finished(self): ...

    def set_closing(self):
        self._is_closing = True


class StatsLogger(NoStatsLogger):
    _total_received: int = 0
    _total_processed: int = 0
    _first: bool = True
    configs = {}
    loggers = {}
    logger_configurable = {
        'interval': int,
    }
    formatter_configurable = {
        'datefmt': str
    }

    @classmethod
    def with_config(cls, parent_logger, cp=None, **kwargs):
        logger_name = f'{parent_logger.name}.stats'
        stats_logger = logging.getLogger(logger_name)
        if stats_logger.isEnabledFor(logging.INFO):
            logger_config_name = f"logger_{logger_name}"
            formatter_name = f"formatter_{parent_logger.name}Stats"
            config = cp.section_as_dict(logger_config_name, **cls.logger_configurable)
            config.update(cp.section_as_dict(formatter_name, **cls.formatter_configurable))
            parent_logger.debug(f'Found config for {parent_logger.name} stats: {config}')
            config.update(**kwargs)
            return partial(cls, stats_logger, **config)
        return partial(cls, NoStatsLogger, stats_logger)

    def __init__(self, logger, extra, interval=0, datefmt="%Y-%M-%d %H:%M:%S"):
        extra = StatsTracker(extra, datefmt=datefmt)
        super().__init__(logger, extra)
        self.connection_started()
        if interval:
            call_cb_periodic(interval, self.periodic_log, fixed_start_time=True)

    def periodic_log(self, first):
        self.extra.end_time = datetime.now()
        tag = 'NEW' if first else 'INTERVAL'
        self.info(tag)
        self._first = False
        self._total_received += self.extra.msgs.received
        self._total_processed += self.extra.msgs.processed
        self.extra = self.extra.reset()

    def on_msg_received(self, msg):
        self.extra.on_msg_received(msg)

    def on_msg_processed(self, msg):
        num_bytes = len(msg.encoded)
        self.extra.on_msg_processed(num_bytes)
        if self._is_closing:
            self.check_last_message_processed()

    def on_msg_sent(self, msg):
        self.extra.on_msg_sent(msg)

    def check_last_message_processed(self):
        if (self._total_received + self.extra.msgs.received) == (self._total_processed + self.extra.msgs.processed):
            self.extra.finish()
            tag = 'ALL' if self._first else 'END'
            self.info(tag)

    def connection_finished(self):
        self.check_last_message_processed()

