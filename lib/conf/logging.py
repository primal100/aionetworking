import logging
from functools import partial
from datetime import datetime

from lib.utils import log_exception
from lib.utils_logging import LoggingDatetime, LoggingTimeDelta, BytesSize, MsgsCount
from lib.wrappers.periodic import call_cb_periodic


class Logger(logging.LoggerAdapter):

    def __init__(self, logger_name, extra=None, **kwargs):
        self._extra = extra or {}
        self._logger_name = logger_name
        logger = logging.getLogger(self._logger_name)
        super().__init__(logger, extra)

    def manage_error(self, exc):
        if exc:
            self.error(log_exception(exc))

    def get_child(self, *args, name='', **kwargs):
        logger_name = f"{self._logger_name}.{name}"
        return self.get_logger(*args, name=logger_name, **kwargs)

    def get_sibling(self, *args, name='', **kwargs):
        name = f'{self.logger.parent.name}.{name}'
        return self.get_logger(*args, name=name, **kwargs)

    def get_logger(self, name='', cls=None, context=None, **kwargs):
        cls = cls or Logger
        if context:
            extra = self._extra.copy()
            extra.update(context)
        else:
            extra = self._extra
        return cls(name, extra, **kwargs)


class StatsLogger(Logger):

    def __init__(self, logger, extra, datefmt="%Y-%M-%d %H:%M:%S"):
        extra = StatsTracker(extra, datefmt=datefmt)
        super().__init__(logger, extra)

    def reset(self):
        self.extra = self.extra.reset()


class ConnectionLogger(Logger):
    _is_closing: bool = False
    configurable = {}

    @classmethod
    def get_config(cls, parent_logger, cp=None, **kwargs):
        stats_logger = parent_logger.get_child('stats')
        if stats_logger.isEnabledFor(logging.INFO):
            klass = ConnectionLoggerStats
        else:
            klass = cls
        from lib import settings
        cp = cp or settings.CONFIG
        config = cp.section_as_dict('ConnectionLogger', **klass.configurable)
        config.update(kwargs)
        return klass, config

    @classmethod
    def with_config(cls, *args, **kwargs):
        klass, config = cls.get_config(*args, **kwargs)
        return partial(klass, **config)

    def __init__(self, logger_name, *args, **kwargs):
        super().__init__(logger_name, *args, **kwargs)
        self._raw_received_logger = self.logger.get_sibling('raw_received')
        self._raw_sent_logger = self.logger.get_sibling('raw_sent')
        self._data_received_logger = self.logger.get_sibling('data_received')
        self._data_sent_logger = self.logger.get_sibling('data_sent')

    def msg_logger(self, msg):
        return self.get_child('msg', context={'msg_obj': msg})

    @property
    def connection_type(self):
        return self.extra['name']

    @property
    def client(self):
        return self.extra['client']

    @property
    def server(self):
        return self.extra['server']

    @property
    def alias(self):
        return self.extra['alias']

    @property
    def peer(self):
        return self.extra['peer']

    def _raw_received(self, data, *args, **kwargs):
        self._raw_received_logger.debug(data, *args, **kwargs)

    def _raw_sent(self, data, *args, **kwargs):
        self._raw_sent_logger.debug(data, *args, **kwargs)

    def _data_received(self, msg_obj, *args, msg='', **kwargs):
        extra = self._extra.copy()
        extra['data'] = msg_obj
        self._data_received_logger.debug(msg, *args, **kwargs)

    def _data_sent(self, msg_obj, *args, msg='', **kwargs):
        extra = self._extra.copy()
        extra['data'] = msg_obj
        self._data_sent_logger.debug(msg, *args, **kwargs)

    def new_connection(self):
        self.info('New %s connection from %s to %s', self.connection_type, self.client, self.server)

    def on_buffer_received(self, data):
        self.debug("Received msg from %s", self.alias)
        self._raw_received(data)

    def on_msg_decoded(self, msg_obj):
        self._data_received(msg_obj)

    def log_decoded_msgs(self, msgs):
        for msg_obj in msgs:
            self.on_msg_decoded(msg_obj)

    def on_sending_decoded_msg(self, msg_obj):
        self._data_sent(msg_obj)

    def on_sending_encoded_msg(self, data):
        self.debug("Sending message to %s", self.peer)
        self._raw_sent(data)

    def on_msg_sent(self, data):
        self.debug('Message sent')

    def on_msg_processed(self, msg): ...

    def connection_finished(self, exc=None):
        self.manage_error(exc)
        self.info('%s connection from %s to %s has been closed', self.connection_type, self.client, self.server)

    def set_closing(self):
        self._is_closing = True


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

    def on_buffer_received(self, msg):
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


class ConnectionLoggerStats(ConnectionLogger):
    _total_received: int = 0
    _total_processed: int = 0
    _first: bool = True
    configs = {}
    loggers = {}
    configurable = ConnectionLogger.configurable.copy()
    configurable.update({
        'interval': int,
        'datefmt': str
    })

    def __init__(self, *args, interval=0, datefmt='%Y-%M-%d %H:%M:%S', **kwargs):
        self._stats_logger = self.logger.get_child('stats', cls=StatsLogger)
        super().__init__(*args, **kwargs)
        self.datefmt = datefmt
        if interval:
            call_cb_periodic(interval, self.periodic_log, fixed_start_time=True)

    def periodic_log(self, first):
        self.extra.end_time = datetime.now()
        tag = 'NEW' if first else 'INTERVAL'
        self.stats(tag)
        self._first = False
        self._total_received += self.extra.msgs.received
        self._total_processed += self.extra.msgs.processed
        self._stats_logger.reset()

    def stats(self, tag):
        self._stats_logger.info(tag)

    def on_buffer_received(self, msg):
        super().on_buffer_received(msg)
        self.extra.on_buffer_received(msg)

    def on_msg_processed(self, msg):
        super().on_msg_processed(msg)
        num_bytes = len(msg.encoded)
        self.extra.on_msg_processed(num_bytes)
        if self._is_closing:
            self.check_last_message_processed()

    def on_msg_sent(self, msg):
        super().on_msg_sent(msg)
        self.extra.on_msg_sent(msg)

    def check_last_message_processed(self):
        if (self._total_received + self.extra.msgs.received) == (self._total_processed + self.extra.msgs.processed):
            self.extra.finish()
            tag = 'ALL' if self._first else 'END'
            self.stats(tag)

    def connection_finished(self, exc=None):
        super().connection_finished(exc=exc)
        self.set_closing()
        self.check_last_message_processed()

