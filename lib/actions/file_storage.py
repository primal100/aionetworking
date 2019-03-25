import asyncio
from dataclasses import dataclass
from pathlib import Path

from .base import BaseReceiverAction
from lib.conf.logging import Logger
from lib.conf.types import RawStr
from lib.utils import plural
from lib.settings import FILE_OPENER

from typing import TYPE_CHECKING, Iterable, AnyStr, Coroutine, Generator, NoReturn
if TYPE_CHECKING:
    from lib.formats.base import BaseMessageObject
else:
    BaseMessageObject = None


@dataclass
class ManagedFile:
    default_logger_name = 'receiver.actions'

    #Dataclass fields
    base_path: Path
    path: Path
    files_dict: dict
    mode: str = 'ab'
    buffering: int = -1
    timeout: int = -5
    attr: str = 'encoded'
    separator: str = ''
    logger: Logger = None

    def __post_init__(self):
        if not self.logger:
            self.logger = Logger(self.default_logger_name)
        self.full_path = self.base_path.joinpath(self.path)
        self.full_path.parent.mkdir(parents=True, exist_ok=True)
        self.files_dict[self.path] = self
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self.manage())

    def write(self, msg: BaseMessageObject) -> NoReturn:
        self._queue.put_nowait(msg)

    async def close(self) -> NoReturn:
        self.logger.debug('Closing file %s', self.path)
        await self.wait_writes_done()
        self._task.cancel()
        await self._task
        self.logger.debug('Closed file %s', self.path)

    def cleanup(self) -> NoReturn:
        del self.files_dict[self.path]
        self.logger.debug('Cleanup completed for %s', self.path)

    async def wait_writes_done(self) -> NoReturn:
        self.logger.debug('Waiting for writes to complete for %s', self.path)
        await self._queue.join()
        self.logger.debug('Writes completed for %s', self.path)

    def _get_data(self, msgs : Iterable[BaseMessageObject]) -> AnyStr:
        return self.separator.join([getattr(msg, self.attr) for msg in msgs]) + self.separator

    async def manage(self) -> NoReturn:
        self.logger.info('Opening file %s', self.full_path)
        async with FILE_OPENER(self.full_path, mode=self.mode, buffering=self.buffering) as f:
            self.logger.debug('File opened')
            try:
                while True:
                    self.logger.debug('Retrieving item from queue for file %s', self.path)
                    msgs = [await asyncio.wait_for(self._queue.get(), timeout=self.timeout)]
                    while not self._queue.empty():
                        try:
                            msgs += self._queue.get_nowait()
                        except asyncio.QueueEmpty:
                            self.logger.info('QueueEmpty error was caught for file %s', self.path)
                    data = self._get_data(msgs)
                    self.logger.debug('Retrieved %s from queue. Writing to file %s.', plural(len(msgs), 'item'), self.path)
                    await f.write(data)
                    await f.flush()
                    self.logger.debug('%s written to file %s', plural(len(data), 'byte'), self.path)
                    for msg in msgs:
                        msg.processed()
                        self._queue.task_done()
                    self.logger.debug('Task done set for %s on file %s', plural(len(msgs), 'item'), self.path)
            except asyncio.TimeoutError:
                self.logger.info('File %s closing due to timeout', self.path)
            except asyncio.CancelledError:
                self.logger.info('File %s closing due to task being cancelled', self.path)
            finally:
                self.cleanup()


class BaseFileStorage(BaseReceiverAction):

    #Dataclass fields
    base_path: Path
    path: RawStr
    attr: str
    mode: str
    separator: str

    def do_one(self, msg: BaseMessageObject):
        raise NotImplementedError

    def _get_full_path(self, msg: BaseMessageObject) -> Path:
        return self.base_path.joinpath(self._get_path(msg))

    def _get_path(self, msg: BaseMessageObject) -> Path:
        return Path(self.path.format(msg=msg))

    def _get_data(self, msg: BaseMessageObject) -> AnyStr:
        data = getattr(msg, self.attr)
        if self.separator:
            data += self.separator
        return data


class FileStorage(BaseFileStorage):
    name = 'File Storage'
    key = 'Filestorage'

    async def _write_to_file(self, path: Path, msg: BaseMessageObject) -> Path:
        msg.logger.debug('Writing to file %s', path)
        data = self._get_data(msg)
        async with FILE_OPENER(path, self.mode) as f:
            await f.write(data)
        msg.logger.debug('Data written to file %s', path)
        msg.processed()
        return path

    def do_one(self, msg: BaseMessageObject) -> Coroutine:
        msg.logger.debug('Running action')
        path = self._get_full_path(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        return self._write_to_file(path, msg)


class BufferedFileStorage(BaseFileStorage):
    name = 'Buffered File Storage'
    key = 'Bufferedfilestorage'

    #Dataclass fields
    buffering: int = -1

    def __post_init__(self):
        super().__post_init__()
        self._files = {}
        self._files_with_outstanding_writes = []

    def _set_outstanding_writes(self, path: Path) -> NoReturn:
        if path not in self._files_with_outstanding_writes:
            self._files_with_outstanding_writes.append(path)

    def _get_file(self, path: Path) -> ManagedFile:
        self.logger.debug('Getting file %s', path)
        try:
            return self._files[path]
        except KeyError:
            return ManagedFile(self.base_path, path, self._files, mode=self.mode, buffering=self.buffering,
                               timeout=self.timeout, logger=self.logger, attr=self.attr, separator=self.separator)

    def _write_to_file(self, path: Path, msg: BaseMessageObject) -> NoReturn:
        f = self._get_file(path)
        f.write(msg)
        self._set_outstanding_writes(path)

    def do_one(self, msg: BaseMessageObject) -> NoReturn:
        msg.logger.debug('Storing message')
        path = self._get_path(msg)
        self._write_to_file(path, msg)

    def do_many(self, msgs: Sequence[BaseMessageObject]) -> Generator[Sequence[BaseMessageObject, None], None, None]:
        return self.do_many_sequential(msgs)

    async def wait_complete(self) -> NoReturn:
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

    async def close(self) -> NoReturn:
        files = list(self._files.values())
        for f in files:
            await f.close()
        i = 0
        while self._files and i < 20:
            await asyncio.sleep(0.1)
            i += 1
