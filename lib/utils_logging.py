from datetime import datetime, timedelta


class LoggingDatetime:

    def __init__(self, datefmt="%Y-%M-%d %H:%M:%S"):
        self.dt = datetime.now()
        self._datefmt = datefmt

    def __getattr__(self, item):
        return getattr(self.dt, item)

    def __str__(self):
        return self.dt.strftime(self._datefmt)

    @property
    def date(self):
        return self.dt.strftime("%D")

    @property
    def time(self):
        return self.dt.strftime("%H:%M:%S")

    @property
    def fulltime(self):
        return self.dt.time()

    @property
    def timestamp(self):
        return self.dt.timestamp()


class LoggingTimeDelta:
    def __init__(self, start_time, end_time):
        if start_time and end_time:
            self.td = end_time.dt - start_time.dt
        else:
            self.td = timedelta()
        self._divisor = self.total_seconds() or 1

    def __getattr__(self, item):
        return getattr(self.td, item)

    def __rtruediv__(self, other):
        return other.__class__(other / self._divisor)

    def __str__(self):
        return str(self.td)

    def __int__(self):
        return int(self.td.total_seconds()) or 1

    @property
    def _minutes(self):
        return self.td.total_seconds() / 60

    @property
    def _hours(self):
        return self._minutes / 60

    @property
    def mins(self):
        return round(self._minutes)

    @property
    def hours(self):
        return round(self._hours)

    @property
    def timestamp(self):
        hours = self.td.days * 24 + self.td.seconds // 3600
        minutes = (self.td.seconds % 3600) // 60
        seconds = self.td.seconds % 60
        return "{0}:{1}:{2}".format(hours, minutes, seconds)

    def full_time(self):
        return self.td


class BytesSizeRate(float):

    def __add__(self, other):
        return self.__class__(super().__add__(other))

    def __sub__(self, other):
        return self.__class__(super().__sub__(other))

    def __mul__(self, other):
        return self.__class__(super().__mul__(other))

    def __floordiv__(self, other):
        return self.__class__(super().__sub__(other))

    def __truediv__(self, other):
        return self.__class__(super().__sub__(other))

    def __rtruediv__(self, other):
        return self.__class__(super().__sub__(int(other)))

    @property
    def bits(self):
        return float(self) * 8

    @property
    def bytes(self):
        return self

    @property
    def kb(self):
        return float(self) / 1024

    @property
    def mb(self):
        return float(self) / 1024 / 1024

    @property
    def gb(self):
        return float(self) / 1024 / 1024 / 1024

    @property
    def tb(self):
        return float(self) / 1024 / 1024 / 1024 / 1024

    def rate(self, interval):
        return self.__class__(self / interval)

    def average(self, num):
        return self / (num or 1)


class BytesSize(int):

    def __add__(self, other):
        return self.__class__(super().__add__(other))

    def __sub__(self, other):
        return self.__class__(super().__sub__(other))

    def __mul__(self, other):
        return self.__class__(super().__mul__(other))

    def __floordiv__(self, other):
        return BytesSizeRate(super().__floordiv__(int(other)))

    def __truediv__(self, other):
        return BytesSizeRate(super().__truediv__(int(other)))

    @property
    def bits(self):
        return int(self) * 8

    @property
    def bytes(self):
        return int(self)

    @property
    def kb(self):
        return int(self) / 1024

    @property
    def mb(self):
        return int(self) / 1024 / 1024

    @property
    def gb(self):
        return int(self) / 1024 / 1024 / 1024

    @property
    def tb(self):
        return int(self) / 1024 / 1024 / 1024 / 1024

    def average(self, num):
        return BytesSizeRate(int(self) / (num or 1))


class MsgsCount:
    sent: int = 0
    received: int = 0
    processed: int = 0
    first_received = None
    last_received = None
    first_sent = None
    last_processed = None

    @property
    def percent_processed(self):
        return self.processed / (self.received or 1)

    @property
    def receive_interval(self):
        return LoggingTimeDelta(self.first_received, self.last_received)

    @property
    def processing_time(self):
        return LoggingTimeDelta(self.first_received, self.last_received)

    @property
    def buffer_receive_rate(self):
        return self.received / self.processing_time

    @property
    def buffer_processing_rate(self):
        return self.processed / self.processing_time
