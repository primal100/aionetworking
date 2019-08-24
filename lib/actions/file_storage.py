from __future__ import annotations
from abc import abstractmethod
import asyncio
from dataclasses import dataclass, field, InitVar
from pathlib import Path

from .base import BaseAction
from lib.conf.logging import Logger, logger_cv
from lib import settings
from lib.compatibility import set_task_name, Protocol
from lib.utils_logging import p
from lib.wrappers.value_waiters import StatusWaiter
from lib.settings import FILE_OPENER

from typing import ClassVar, AnyStr
from lib.formats.types import MessageObjectType


@dataclass
class ManagedFile:

    path: Path
    mode: str = 'ab'
    buffering: int = -1
    timeout: int = 5
    logger: Logger = field(default_factory=logger_cv.get)
    _status: StatusWaiter = field(default_factory=StatusWaiter, init=False)
    previous: ManagedFile = field(default=None)
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False, compare=False)
    _open_files: ClassVar = {}

    @classmethod
    def open(cls, path, *args, **kwargs) -> ManagedFile:
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
    async def close_all(cls) -> None:
        if cls._open_files:
            await asyncio.wait([f.close() for f in cls._open_files.values()])

    @classmethod
    def num_files(cls):
        return len(cls._open_files)

    def __post_init__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._task = asyncio.create_task(self.manage())
        set_task_name(self._task, f"ManagedFile:{self.path.name}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb): ...

    def is_closing(self):
        return self._status.is_stopping_or_stopped()

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
        fut = asyncio.Future()
        await self._queue.put((data, fut))
        await fut

    async def close(self) -> None:
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
            self.logger.info('Opening file %s', self.path)
            async with FILE_OPENER(self.path, mode=self.mode, buffering=self.buffering) as f:
                self.logger.debug('File %s opened', self.path)
                self._status.set_started()
                while True:
                    self.logger.debug('Retrieving item from queue for file %s', self.path)
                    data, fut = await asyncio.wait_for(self._queue.get(), timeout=self.timeout)
                    futs = [fut]
                    try:
                        while not self._queue.empty():
                            try:
                                item, fut = self._queue.get_nowait()
                                data += item
                                futs.append(fut)
                            except asyncio.QueueEmpty:
                                self.logger.info('QueueEmpty error was caught for file %s', self.path)
                        self.logger.debug('Retrieved %s from queue. Writing to file %s.', p.no('item', len(futs)), self.path)
                        await f.write(data)
                        await f.flush()
                        self.logger.debug('%s written to file %s', p.no('byte', len(data)), self.path)
                        for fut in futs:
                            fut.set_result(True)
                    except Exception as e:
                        for fut in futs:
                            fut.set_exception(e)
                    finally:
                        for _ in futs:
                            self._queue.task_done()
                    self.logger.debug('Task done set for %s on file %s', p.no('item', len(futs)), self.path)
        except asyncio.TimeoutError:
            self.logger.info('File %s closing due to timeout', self.path)
        except asyncio.CancelledError as e:
            self.logger.info('File %s closing due to task being cancelled', self.path)
            raise e
        finally:
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

    def _get_full_path(self, msg: MessageObjectType) -> Path:
        return self.base_path / self._get_path(msg)

    def _get_path(self, msg: MessageObjectType) -> Path:
        return Path(self.path.format(msg=msg))

    def _get_data(self, msg: MessageObjectType) -> AnyStr:
        data = getattr(msg, self.attr)
        if self.separator:
            data += self.separator
        return data

    @abstractmethod
    async def _write_to_file(self, path: Path, data: AnyStr): ...

    async def write_one(self, msg: MessageObjectType) -> Path:
        path = self._get_full_path(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        msg.logger.debug('Writing to file %s', path)
        data = self._get_data(msg)
        await self._write_to_file(path, data)
        msg.logger.debug('Data written to file %s', path)
        return path

    async def do_one(self, msg: MessageObjectType) -> None:
        await self.write_one(msg)


@dataclass
class FileStorage(BaseFileStorage):
    name = 'File Storage'

    async def _write_to_file(self, path: Path, data: AnyStr) -> None:
        async with FILE_OPENER(path, self.mode) as f:
            await f.write(data)


@dataclass
class BufferedFileStorage(BaseFileStorage):
    name = 'Buffered File Storage'
    mode: str = 'a'

    buffering: int = -1

    async def _write_to_file(self, path: Path, data: AnyStr) -> None:
        async with ManagedFile.open(path, mode=self.mode, buffering=self.buffering, timeout=self.timeout,
                                    logger=self.logger) as f:
            await f.write(data)

    async def close(self) -> None:
        await ManagedFile.close_all()
