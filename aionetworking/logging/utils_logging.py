from datetime import datetime, timedelta, time
import inflect

from typing import Any


class LoggingDatetime:

    def __init__(self, datefmt: str = "%Y-%M-%d %H:%M:%S"):
        self.dt = datetime.now()
        self._datefmt = datefmt

    def __gt__(self, other):
        return self.dt > other.dt

    def __ge__(self, other):
        return self.dt >= other.dt

    def __le__(self, other):
        return self.dt >= other.dt

    def __lt__(self, other):
        return self.dt < other.dt

    def __eq__(self, other):
        return self.dt == other.dt

    def __getattr__(self, item: str) -> Any:
        return getattr(self.dt, item)

    def __str__(self) -> str:
        return self.dt.strftime(self._datefmt)

    @property
    def date(self) -> str:
        return self.dt.strftime("%D")

    @property
    def time(self) -> str:
        return self.dt.strftime("%H:%M:%S")

    @property
    def fulltime(self) -> time:
        return self.dt.time()

    @property
    def timestamp(self) -> float:
        return self.dt.timestamp()


class LoggingTimeDelta:
    def __init__(self, start_time: LoggingDatetime, end_time: LoggingDatetime):
        if start_time and end_time:
            self.td = end_time.dt - start_time.dt
        else:
            self.td = timedelta()
        self._divisor = self.td.total_seconds() or 1.00

    def __int__(self):
        return int(self._divisor)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.td, item)

    def __rtruediv__(self, other: float) -> float:
        return other.__class__(other / self._divisor)

    def __str__(self) -> str:
        return str(self.td)

    def __float__(self) -> float:
        return self._divisor

    @property
    def _minutes(self) -> float:
        return self.td.total_seconds() / 60

    @property
    def _hours(self) -> float:
        return self._minutes / 60

    @property
    def mins(self) -> int:
        return round(self._minutes)

    @property
    def hours(self) -> int:
        return round(self._hours)

    @property
    def timestamp(self) -> str:
        hours = self.td.days * 24 + self.td.seconds // 3600
        minutes = (self.td.seconds % 3600) // 60
        seconds = self.td.seconds % 60
        return "{0}:{1}:{2}".format(hours, minutes, seconds)

    def full_time(self) -> timedelta:
        return self.td


class BytesSizeRate(float):

    def __add__(self, other) -> float:
        return self.__class__(super().__add__(other))

    def __sub__(self, other) -> float:
        return self.__class__(super().__sub__(other))

    def __mul__(self, other) -> float:
        return self.__class__(super().__mul__(other))

    def __floordiv__(self, other) -> float:
        return self.__class__(super().__sub__(other))

    def __truediv__(self, other) -> float:
        return self.__class__(super().__sub__(other))

    def __rtruediv__(self, other) -> float:
        return self.__class__(super().__sub__(float(other)))

    @property
    def bits(self) -> float:
        return float(self) * 8

    @property
    def bytes(self) -> float:
        return float(self)

    @property
    def kb(self) -> float:
        return float(self) / 1024

    @property
    def mb(self) -> float:
        return float(self) / 1024 / 1024

    @property
    def gb(self) -> float:
        return float(self) / 1024 / 1024 / 1024

    @property
    def tb(self) -> float:
        return float(self) / 1024 / 1024 / 1024 / 1024

    def rate(self, interval: float) -> float:
        return self.__class__(self / interval)

    def average(self, num) -> float:
        return self / (num or 1)


class BytesSize(int):

    def __add__(self, other) -> 'BytesSize':
        return BytesSize(other + int(self))

    def __floordiv__(self, other) -> BytesSizeRate:
        return BytesSizeRate(float(self).__floordiv__(float(other)))

    def __truediv__(self, other) -> BytesSizeRate:
        return BytesSizeRate(float(self).__truediv__(float(other)))

    @property
    def bits(self):
        return int(self) * 8

    @property
    def bytes(self) -> int:
        return int(self)

    @property
    def kb(self) -> float:
        return int(self) / 1024

    @property
    def mb(self) -> float:
        return int(self) / 1024 / 1024

    @property
    def gb(self) -> float:
        return int(self) / 1024 / 1024 / 1024

    @property
    def tb(self) -> float:
        return int(self) / 1024 / 1024 / 1024 / 1024

    def __repr__(self):
        return f"{int(self)} bytes"


class MsgsCount:
    sent: int = 0
    received: int = 0
    processed: int = 0
    filtered: int = 0
    failed: int = 0
    first_received = None
    last_received = None
    first_sent = None
    last_sent = None
    last_processed = None

    @property
    def total_done(self) -> int:
        return self.processed + self.filtered + self.failed

    @property
    def percent_filtered(self) -> float:
        return self.filtered / (self.total_done or 1)

    @property
    def percent_failed(self) -> float:
        return self.failed / (self.total_done or 1)

    @property
    def percent_processed(self) -> float:
        return self.processed / (self.total_done or 1)

    @property
    def receive_interval(self) -> LoggingTimeDelta:
        return LoggingTimeDelta(self.first_received, self.last_received)

    @property
    def send_rate(self) -> float:
        return self.sent / self.send_interval

    @property
    def send_interval(self) -> LoggingTimeDelta:
        return LoggingTimeDelta(self.first_sent, self.last_sent)

    @property
    def processing_time(self) -> LoggingTimeDelta:
        return LoggingTimeDelta(self.first_received, self.last_processed)

    @property
    def buffer_receive_rate(self) -> float:
        return self.received / self.receive_interval

    @property
    def buffer_processing_rate(self) -> float:
        return self.received / self.processing_time

    @property
    def processing_rate(self) -> float:
        return self.processed / self.processing_time


p = inflect.engine()
