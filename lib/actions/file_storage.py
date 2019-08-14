from __future__ import annotations
from abc import ABC
import asyncio
from dataclasses import dataclass, field, InitVar
from pathlib import Path

from .base import BaseAction
from lib.conf.logging import Logger
from lib import settings
from lib.utils_logging import p
from lib.settings import FILE_OPENER

from typing import TYPE_CHECKING, ClassVar, Iterable, Sequence, List, Tuple, AnyStr
if TYPE_CHECKING:
    from lib.formats.base import BaseMessageObject
else:
    BaseMessageObject = None


@dataclass
class ManagedFile:

    path: Path
    mode: str = 'ab'
    buffering: int = -1
    timeout: int = 5
    attr: str = 'encoded'
    separator: str = b''
    logger: Logger = Logger('receiver.actions')
    _task_started: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False, hash=False, compare=False )
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False, repr=False, hash=False, compare=False)
    _open_files: ClassVar = {}

    @classmethod
    def get_file(cls, path, *args, **kwargs) -> ManagedFile:
        try:
            return cls._open_files[path]
        except KeyError:
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

    def _cleanup(self) -> None:
        del self._open_files[self.path]
        self.logger.debug('Cleanup completed for %s', self.path)

    def _get_data(self, msgs : Iterable[BaseMessageObject]) -> AnyStr:
        return self.separator.join([getattr(msg, self.attr) for msg in msgs]) + self.separator

    def write(self, msg: BaseMessageObject) -> None:
        self._queue.put_nowait(msg)

    async def close(self) -> None:
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
                self.logger.debug('File opened')
                while True:
                    self.logger.debug('Retrieving item from queue for file %s', self.path)
                    msgs = [await asyncio.wait_for(self._queue.get(), timeout=self.timeout)]
                    while not self._queue.empty():
                        try:
                            msgs.append(self._queue.get_nowait())
                        except asyncio.QueueEmpty:
                            self.logger.info('QueueEmpty error was caught for file %s', self.path)
                    data = self._get_data(msgs)
                    self.logger.debug('Retrieved %s from queue. Writing to file %s.', p.no('item', msgs), self.path)
                    await f.write(data)
                    await f.flush()
                    self.logger.debug('%s written to file %s', p.no('byte', data), self.path)
                    for msg in msgs:
                        msg.processed()
                        self._queue.task_done()
                    self.logger.debug('Task done set for %s on file %s', p.no('item', msgs), self.path)
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
        if binary:
            self.mode += 'b'
            if isinstance(self.separator, str):
                self.separator = self.separator.encode()

    def __getstate__(self):
        state = super().__getstate__()
        state['binary'] = 'b' in self.mode
        return state

    def _get_full_path(self, msg: BaseMessageObject) -> Path:
        return self.base_path / self._get_path(msg)

    def _get_path(self, msg: BaseMessageObject) -> Path:
        return Path(self.path.format(msg=msg))

    def _get_data(self, msg: BaseMessageObject) -> AnyStr:
        data = getattr(msg, self.attr)
        if self.separator:
            data += self.separator
        return data


@dataclass
class FileStorage(BaseFileStorage):
    name = 'File Storage'

    async def _write_to_file(self, path: Path, msg: BaseMessageObject) -> Path:
        msg.logger.debug('Writing to file %s', path)
        data = self._get_data(msg)
        async with FILE_OPENER(path, self.mode) as f:
            await f.write(data)
        msg.logger.debug('Data written to file %s', path)
        msg.processed()
        return path

    async def async_do_one(self, msg: BaseMessageObject):
        msg.logger.debug('Running action')
        path = self._get_full_path(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        return await self._write_to_file(path, msg)


@dataclass
class BufferedFileStorage(BaseFileStorage):
    name = 'Buffered File Storage'
    mode: str = 'a'

    buffering: int = -1
    _files_with_outstanding_writes: List = field(default_factory=list)

    def _set_outstanding_writes(self, path: Path) -> None:
        if path not in self._files_with_outstanding_writes:
            self._files_with_outstanding_writes.append(path)

    def _get_file(self, path: Path) -> ManagedFile:
        self.logger.debug('Getting file %s', path)
        full_path = self.base_path / path
        return ManagedFile.get_file(full_path, mode=self.mode, buffering=self.buffering,
                                    timeout=self.timeout, logger=self.logger, attr=self.attr, separator=self.separator)

    def _write_to_file(self, path: Path, msg: BaseMessageObject) -> None:
        f = self._get_file(path)
        f.write(msg)
        self._set_outstanding_writes(path)

    def do_one(self, msg: BaseMessageObject) -> None:
        msg.logger.debug('Storing message')
        path = self._get_path(msg)
        self._write_to_file(path, msg)

    async def wait_complete(self) -> None:
        try:
            self.logger.debug('Waiting for outstanding writes to complete')
            self.logger.debug(self._files_with_outstanding_writes)
            for path in self._files_with_outstanding_writes:
                f = self._get_file(path)
                await f.wait_writes_done()
            self.logger.debug('All outstanding writes have been completed')
        finally:
            self._files_with_outstanding_writes.clear()
            self.logger.debug(self._files_with_outstanding_writes)

    async def close(self) -> None:
        await self.wait_complete()
        await ManagedFile.close_all()
