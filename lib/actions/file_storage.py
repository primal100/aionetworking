from __future__ import annotations
from abc import abstractmethod
import asyncio
import time
from dataclasses import dataclass, field, InitVar
from pathlib import Path

from .base import BaseAction
from lib.conf.logging import Logger, logger_cv
from lib import settings
from lib.compatibility import set_task_name, Protocol
from lib.utils_logging import p
from lib.wrappers.value_waiters import StatusWaiter

from typing import ClassVar, AnyStr, List
from lib.formats.types import MessageObjectType


class DataHolder:

    def __init__(self, max: int = 80000):
        self._data = b''
        self._futs = []
        self._max = max
        self._all_tasks_done_event = asyncio.Event()
        self._has_event = asyncio.Event()
        self._not_full_event = asyncio.Event()
        self._not_full_event.set()
        self._to_process = 0

    async def put(self, b: bytes) -> asyncio.Future:
        fut = asyncio.Future()
        self._futs.append(fut)
        await self._not_full_event.wait()
        self._to_process += len(b)
        self._all_tasks_done_event.clear()
        self._has_event.set()
        self._data += b
        if self._to_process > self._max:
            self._not_full_event.clear()
        return fut

    def get_nowait(self):
        if not self._data:
            raise asyncio.QueueEmpty
        d = self._data
        self._has_event.clear()
        self._not_full_event.set()
        self._data = b''
        futs = self._futs.copy()
        self._futs = []
        return d, futs

    async def get(self):
        if not self._data:
            await self._has_event.wait()
        return self.get_nowait()

    async def join(self):
        await self._all_tasks_done_event.wait()

    def task_done(self, num: int, futs: List[asyncio.Future], exc: BaseException = None):
        if exc:
            for fut in futs:
                fut.set_exception(exc)
        else:
            for fut in futs:
                fut.set_result(True)
        self._to_process -= num
        if self._to_process == 0:
            self._all_tasks_done_event.set()


@dataclass
class ManagedFile:

    path: str
    mode: str = 'ab'
    buffering: int = -1
    timeout: int = 10
    max_concat: int = 1000
    logger: Logger = field(default_factory=logger_cv.get)
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)
    previous: ManagedFile = field(default=None)
    _queue: DataHolder = field(default_factory=DataHolder, init=False, repr=False, hash=False, compare=False)
    _open_files: ClassVar = {}

    @classmethod
    def open(cls, path: str, *args, **kwargs) -> ManagedFile:
        try:
            f = cls._open_files[path]
            if not f.is_closing():
                return f
            kwargs['previous'] = f
        except KeyError:
            pass
        f = cls(path, *args, **kwargs)
        cls._open_files[path] = f
        return f

    @classmethod
    async def close_all(cls, base_path: Path = None) -> None:
        if base_path:
            files = [f for f in cls._open_files.values() if f.is_in(base_path)]
        else:
            files = [f for f in cls._open_files.values()]
        if files:
            await asyncio.wait([f.close() for f in files])

    @classmethod
    def num_files(cls):
        return len(cls._open_files)

    def __post_init__(self):
        #self.path.parent.mkdir(parents=True, exist_ok=True)
        self._task = asyncio.create_task(self.manage())
        set_task_name(self._task, f"ManagedFile:{self.path}")

    def is_in(self, path: Path) -> bool:
        try:
            Path(self.path).relative_to(path)
            return True
        except ValueError:
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb): ...

    def is_closing(self):
        return self._status.has_started() and self._status.is_stopping_or_stopped()

    async def wait_closed(self):
        return await self._status.wait_stopped()

    async def wait_has_started(self):
        return await self._status.wait_has_started()

    def _cleanup(self) -> None:
        self._status.set_stopping()
        if self._open_files[self.path] == self:
            del self._open_files[self.path]
        self.logger.debug('Cleanup completed for %s', self.path)
        self._status.set_stopped()

    async def write(self, data: AnyStr) -> None:
        fut = await self._queue.put(data)
        await fut

    async def close(self) -> None:
        if not self.is_closing():
            await self._status.wait_started()
            self._status.set_stopping()
            self.logger.debug('Closing file %s', self.path)
            if not self._task.done():
                await self.wait_has_started()
                await self.wait_writes_done()
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            else:
                self.logger.debug('File %s already closed', self.path)
            self.logger.debug('Closed file %s', self.path)

    async def wait_writes_done(self) -> None:
        self.logger.debug('Waiting for writes to complete for %s', self.path)
        done, pending = await asyncio.wait([self._queue.join(), self._task], return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            if d.exception():                       #3.8 assignment expressions
                self.logger.error(d.exception())
                await d
        self.logger.debug('Writes completed for %s', self.path)

    async def manage(self) -> None:
        if self.previous:
            await self.previous.wait_closed()
        try:
            self._status.set_starting()
            #self.logger.info('Opening file %s', self.path)
            async with settings.FILE_OPENER(self.path, mode=self.mode, buffering=self.buffering) as f:
                #self.logger.debug('File %s opened', self.path)
                self._status.set_started()
                #write_seconds = 0
                #start_time = time.time()
                while True:
                    #self.logger.info('Retrieving item from queue for file %s.', self.path)
                    data, futs = await asyncio.wait_for(self._queue.get(), timeout=self.timeout)
                    #self.logger.info('Retrieved %s from queue. Writing to file %s.', p.no('item', len(futs)),
                    #                     self.path)
                    #start = time.time()
                    #try:
                    await f.write(data)
                    await f.flush()
                    asyncio.get_event_loop().call_soon(self._queue.task_done, len(data), futs)
                    #except Exception as e:
                    #    self._queue.task_done(len(data), futs, exc=e)
                    #finally:
                    #    pass
                        #end = time.time()
                        #write_seconds += (end - start)
                        #self.logger.info('%s written to file %s', p.no('byte', len(data)), self.path)
        except asyncio.TimeoutError:
            self.logger.info('File %s closing due to timeout', self.path)
        except asyncio.CancelledError as e:
            self.logger.info('File %s closing due to task being cancelled', self.path)
            raise e
        finally:
            #end_time = time.time()
            #self.logger.info('Was writing to file for %s seconds', write_seconds)
            #total_seconds = end_time - start_time
            #self.logger.info('Was writing to file %s percent of the time', (write_seconds / total_seconds * 100))
            self._cleanup()


def default_data_dir():
    return settings.DATA_DIR


@dataclass
class BaseFileStorage(BaseAction, Protocol):

    base_path: Path = field(default_factory=default_data_dir, metadata={'pickle': True})
    path: str = ''
    attr: str = 'encoded'
    mode: str = 'w'
    separator: AnyStr = ''
    binary: InitVar[bool] = False

    def __post_init__(self, binary):
        if binary and 'b' not in self.mode:
            self.mode += 'b'
            if isinstance(self.separator, str):
                self.separator = self.separator.encode()
        self._status.is_started()
        self.base_path.mkdir(exist_ok=True, parents=True)
        self._file_path = str(self.base_path / 'data.bin')

    async def start(self) -> None:
        ManagedFile.open(self._file_path)
        self._status.set_started()

    def _get_full_path(self, msg: AnyStr) -> str:
        return self._file_path
        #return self.base_path / self._get_path(msg)

    def _get_path(self, msg: AnyStr) -> Path:
        return Path(self.path.format(msg=msg))

    def _get_data(self, msg: AnyStr) -> AnyStr:
        data = getattr(msg, self.attr)
        if self.separator:
            data += self.separator
        return data

    @abstractmethod
    async def _write_to_file(self, path: str, data: AnyStr): ...

    async def write_one(self, msg: AnyStr) -> None:
        #path = self._get_full_path(msg)
        #msg.logger.debug('Writing to file %s', path)
        #data = self._get_data(msg)
        await self._write_to_file(self._file_path, msg)
        #msg.logger.debug('Data written to file %s', path)

    async def do_one(self, msg: AnyStr) -> None:
        await self.write_one(msg)


@dataclass
class FileStorage(BaseFileStorage):
    name = 'File Storage'

    async def _write_to_file(self, path: str, data: AnyStr) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        async with settings.FILE_OPENER(path, self.mode) as f:
            await f.write(data)


@dataclass
class BufferedFileStorage(BaseFileStorage):
    name = 'Buffered File Storage'
    mode: str = 'a'
    _qsize: int = 0

    close_file_after_inactivity: int = 10
    buffering: int = -1
    max_concat: int = 1000

    async def _write_to_file(self, path: str, data: AnyStr) -> None:
        f = ManagedFile.open(path, mode=self.mode, buffering=self.buffering,
                             timeout=self.close_file_after_inactivity, logger=self.logger,
                             max_concat=self.max_concat)
        await f.write(data)

    async def close(self) -> None:
        self._status.set_stopping()
        await ManagedFile.close_all(base_path=self.base_path)
        self._status.set_stopped()

    def set_qsize(self, i):
        self.logger.info('setting expected qsize to %s', i)
        self._qsize = i