from __future__ import annotations
from abc import ABC
import asyncio
from dataclasses import dataclass, field, InitVar
from pathlib import Path

from .base import BaseAction
from lib.conf.logging import Logger
from lib import settings
from lib.compatibility import set_task_name
from lib.utils_logging import p
from lib.settings import FILE_OPENER

from typing import ClassVar, Iterable,  List, AnyStr
from lib.formats.types import MessageObjectType


@dataclass
class ManagedFile:

    path: Path
    mode: str = 'ab'
    buffering: int = -1
    timeout: int = 5
    attr: str = 'encoded'
    separator: str = b''
    logger: Logger = Logger('receiver.actions')
    _task_started: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False, hash=False, compare=False)
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False, compare=False)
    _close_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _all_closed_fut: asyncio.Future = field(default_factory=asyncio.Future, init=None)
    _open_files: ClassVar = {}

    @classmethod
    def get_file(cls, path, *args, **kwargs) -> ManagedFile:
        try:
            f = cls._open_files[path]
            return f
        except KeyError:
            pass
        f = cls(path, *args, **kwargs)
        cls._open_files[path] = f
        return f

    @classmethod
    async def close_all(cls) -> None:
        files = list(cls._open_files.values())
        for f in files:
            await f.close()
        i = 0
        while cls._open_files and i < 20:
            await asyncio.sleep(0.1)
            i += 1

    @classmethod
    def num_files(cls):
        return len(cls._open_files)

    def __post_init__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._task = asyncio.create_task(self.manage())
        set_task_name(self._task, f"ManagedFile:{self.path.name}")

    def is_closing(self) -> bool:
        return self._close_lock.locked()

    async def wait_closed(self) -> None:
        await self._close_lock.acquire()

    def _cleanup(self) -> None:
        if self._open_files[self.path] == self:
            del self._open_files[self.path]
        if self._close_lock.locked():
            self._close_lock.release()
        self.logger.debug('Cleanup completed for %s', self.path)

    def _get_data(self, msgs : Iterable[MessageObjectType]) -> AnyStr:
        return self.separator.join([getattr(msg, self.attr) for msg in msgs]) + self.separator

    async def write(self, msg: MessageObjectType) -> None:
        fut = asyncio.Future()
        await self._queue.put((msg, fut))
        await fut

    async def close(self) -> None:
        if not self._close_lock.locked():
            await self._close_lock.acquire()
            self.logger.debug('Closing file %s', self.path)
            if not self._task.done():
                await self._task_started.wait()
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
        try:
            self._task_started.set()
            self.logger.info('Opening file %s', self.path)
            async with FILE_OPENER(self.path, mode=self.mode, buffering=self.buffering) as f:
                self.logger.debug('File %s opened', self.path)
                while True:
                    self.logger.debug('Retrieving item from queue for file %s', self.path)
                    msg, fut = await asyncio.wait_for(self._queue.get(), timeout=self.timeout)
                    msgs = [msg]
                    futs = [fut]
                    try:
                        while not self._queue.empty():
                            try:
                                msg, fut = self._queue.get_nowait()
                                msgs.append(msg)
                                futs.append(fut)
                            except asyncio.QueueEmpty:
                                self.logger.info('QueueEmpty error was caught for file %s', self.path)
                        data = self._get_data(msgs)
                        self.logger.debug('Retrieved %s from queue. Writing to file %s.', p.no('item', len(msgs)), self.path)
                        await f.write(data)
                        await f.flush()
                        self.logger.debug('%s written to file %s', p.no('byte', len(data)), self.path)
                        for fut in futs:
                            fut.set_result(True)
                    except Exception as e:
                        for fut in futs:
                            fut.set_exception(e)
                    finally:
                        for _ in msgs:
                            self._queue.task_done()
                    self.logger.debug('Task done set for %s on file %s', p.no('item', len(msgs)), self.path)
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
class BaseFileStorage(BaseAction, ABC):

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


@dataclass
class FileStorage(BaseFileStorage):
    name = 'File Storage'

    async def _write_to_file(self, path: Path, msg: MessageObjectType) -> Path:
        msg.logger.debug('Writing to file %s', path)
        data = self._get_data(msg)
        async with FILE_OPENER(path, self.mode) as f:
            await f.write(data)
        msg.logger.debug('Data written to file %s', path)
        msg.processed()
        return path

    async def do_one(self, msg: MessageObjectType):
        path = self._get_full_path(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        return await self._write_to_file(path, msg)


@dataclass
class BufferedFileStorage(BaseFileStorage):
    name = 'Buffered File Storage'
    mode: str = 'a'

    buffering: int = -1
    _files_with_outstanding_writes: List = field(default_factory=list, init=False)
    _close_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def _set_outstanding_writes(self, path: Path) -> None:
        if path not in self._files_with_outstanding_writes:
            self._files_with_outstanding_writes.append(path)

    def _get_file(self, path: Path) -> ManagedFile:
        full_path = self.base_path / path
        f = ManagedFile.get_file(full_path, mode=self.mode, buffering=self.buffering,
                                 timeout=self.timeout, logger=self.logger, attr=self.attr, separator=self.separator)
        return f

    async def _write_to_file(self, path: Path, msg: MessageObjectType) -> None:
        f = self._get_file(path)
        self._set_outstanding_writes(path)
        await f.write(msg)
        msg.processed()

    async def do_one(self, msg: MessageObjectType) -> None:
        if self._close_lock.locked():
            self._close_lock.release()
        msg.logger.debug('Storing message %s', msg.uid)
        path = self._get_path(msg)
        await self._write_to_file(path, msg)

    async def wait_complete(self) -> None:
        try:
            self.logger.debug('Waiting for outstanding writes to complete')
            for path in self._files_with_outstanding_writes:
                f = self._get_file(path)
                await f.wait_writes_done()
            self.logger.debug('All outstanding writes have been completed')
        finally:
            self._files_with_outstanding_writes.clear()
            self.logger.debug(self._files_with_outstanding_writes)

    async def close(self) -> None:
        if not self._close_lock.locked():
            await self._close_lock.acquire()
            await self.wait_complete()
            await ManagedFile.close_all()
