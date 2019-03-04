from logging import LoggerAdapter
from datetime import datetime
import time

from lib.utils import  log_exception
from lib.wrappers.periodic import call_cb_periodic


class ConnectionLogger(LoggerAdapter):

    def manage_error(self, exc):
        if exc:
            self.error(log_exception(exc))


measures = {
    'byte': 1,
    'kb': 1024,
    'mb': 1048576,
    'gb': 1073741824
}


class StatsTracker:
    sent_msgs: int = 0
    sent_bytes: int = 0
    received_msgs: int = 0
    received_bytes: int = 0
    processed_msgs: int = 0
    processed_bytes: int = 0
    first_message_received: datetime = None
    first_message_sent: datetime = None
    last_message_received: datetime = None
    last_message_processed: datetime = None

    @property
    def processing_rate_bytes(self):
        return self.processed_bytes / self.processing_time.seconds

    @property
    def receive_rate_bytes(self):
        return self.received_bytes / (self.last_message_received - self.last_message_processed).total_seconds()

    @property
    def buffer_processing_rate(self):
        return self.processed_msgs / self.processing_time.total_seconds()

    @property
    def buffer_receive_rate(self):
        return self.received_msgs / (self.last_message_received - self.last_message_processed).total_seconds()

    @property
    def processing_time(self):
        return self.last_message_processed - self.first_message_received

    @property
    def average_buffer_bytes(self):
        return self.received_bytes / self.received_msgs

    @property
    def average_sent_bytes(self):
        return self.sent_bytes / self.sent_msgs

    def __iter__(self):
        return self.properties.__iter__()

    def __getitem__(self, item):
        if "__" in item:
            attr, measure = item.split('__')
            num_bytes = getattr(self, "%s_bytes" % attr)
            return num_bytes / measures[measure]
        return self.properties.get(item, getattr(self, item, None))

    def __init__(self, properties):
        self.properties = properties
        self.start_time = datetime.now()


class NoStatsLogger(LoggerAdapter):

    def connection_started(self): ...

    def on_msg_received(self, msg): ...

    def on_msg_processed(self, num_bytes): ...

    def on_msg_sent(self, msg): ...

    def connection_finished(self): ...


class StatsLogger(NoStatsLogger):
    _total_received: int = 0
    _total_processed: int = 0

    def __init__(self, logger, extra, transport, interval=0):
        stats = StatsTracker(extra)
        super().__init__(logger, stats)
        self.transport = transport
        if interval:
            call_cb_periodic(interval, self.periodic_log, fixed_start_time=True)
        self.connection_started()

    def periodic_log(self, first):
        self.extra.end_time = datetime.now()
        tag = 'NEW' if first else 'INTERVAL'
        self.info(tag)
        self._total_received += self.extra.received_msgs
        self._total_processed += self.extra.processed_msgs
        self.extra = StatsTracker(self.extra.properties)

    def connection_started(self):
        self.extra.start_time = time.time()

    def on_msg_received(self, msg):
        if not self.extra.first_message_received:
            self.extra.first_message_received = time.time()
        self.extra.last_message_received = time.time()
        self.extra.received_msgs += 1
        self.extra.received_bytes += len(msg)

    def on_msg_processed(self, num_bytes):
        self.extra.last_message_processed = time.time()
        self.extra.processed_msgs += 1
        if self.transport.is_closing():
            self.check_last_message_processed()

    def on_msg_sent(self, msg):
        if not self.extra.first_message_sent:
            self.extra.first_message_sent = time.time()
        self.extra.sent_msgs += 1
        self.extra.sent_bytes += len(msg)

    def check_last_message_processed(self):
        if (self._total_received + self.extra.received_msgs) == (self._total_processed + self.extra.processed_msgs):
            self.extra.end_time = datetime.now()
            self.info('END')

    def connection_finished(self):
        self.extra.end_time = time.time()
        self.check_last_message_processed()
