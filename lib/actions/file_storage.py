import asyncio
import logging
from pathlib import Path

from .base import BaseServerAction
from lib.conf import RawStr
from lib.utils import plural
from lib.settings import FILE_OPENER
from lib import settings


class ManagedFile:
    f = None

    def __init__(self, base_path, path, files_dict, mode='ab', buffering=-1, timeout=5, logger=None,
                 attr='encoded', separator=''):
        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger('receiver')
        self.full_path = base_path.joinpath(path)
        self.full_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.files_dict = files_dict
        self.files_dict[path] = self
        self.mode = mode
        self.buffering = buffering
        self.timeout = timeout
        self.files_dict = files_dict
        self.files_dict[path] = self
        self.attr = attr
        self.separator = separator
        self.queue = asyncio.Queue()
        self.task = asyncio.create_task(self.manage())

    def write(self, msg):
        self.queue.put_nowait(msg)

    async def close(self):
        self.logger.debug('Closing file %s', self.path)
        await self.wait_writes_done()
        self.task.cancel()
        await self.task
        self.logger.debug('Closed file %s', self.path)

    def cleanup(self):
        del self.files_dict[self.path]
        self.logger.debug('Cleanup completed for %s', self.path)

    async def wait_writes_done(self):
        self.logger.debug('Waiting for writes to complete for %s', self.path)
        await self.queue.join()
        self.logger .debug('Writes completed for %s', self.path)

    def get_data(self, msgs):
        return self.separator.join([getattr(msg, self.attr) for msg in msgs]) + self.separator

    async def manage(self):
        self.logger.info('Opening file %s', self.full_path)
        async with FILE_OPENER(self.full_path, mode=self.mode, buffering=self.buffering) as f:
            self.logger.debug('File opened')
            try:
                while True:
                    self.logger.debug('Retrieving item from queue for file %s', self.path)
                    msgs = [await asyncio.wait_for(self.queue.get(), timeout=self.timeout)]
                    while not self.queue.empty():
                        try:
                            msgs += self.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            self.logger.info('QueueEmpty error was caught for file %s', self.path)
                    data = self.get_data(msgs)
                    self.logger.debug('Retrieved %s from queue. Writing to file %s.', plural(len(msgs), 'item'), self.path)
                    await f.write(data)
                    await f.flush()
                    self.logger.debug('%s written to file %s', plural(len(data), 'byte'), self.path)
                    for msg in msgs:
                        msg.processed()
                        self.queue.task_done()
                    self.logger.debug('Task done set for %s on file %s', plural(len(msgs), 'item'), self.path)
            except asyncio.TimeoutError:
                self.logger.info('File %s closing due to timeout', self.path)
            except asyncio.CancelledError:
                self.logger.info('File %s closing due to task being cancelled', self.path)
            finally:
                self.cleanup()


class BaseFileStorage(BaseServerAction):

    configurable = BaseServerAction.configurable
    configurable.update({
        'basepath': Path,
        'path': RawStr,
        'attr': str,
        'mode': str,
        'separator': str
    })

    def __init__(self, basepath, path, attr='encoded', mode='wb', separator=None, **kwargs):
        super(BaseFileStorage, self).__init__(**kwargs)
        self.base_path = basepath
        self.path = path
        self.attr = attr
        self.mode = mode
        self.separator = separator

    def do_one(self, msg):
        raise NotImplementedError

    def get_full_path(self, msg):
        return self.base_path.joinpath(self.get_path(msg))

    def get_path(self, msg):
        return self.path.format(msg=msg)

    def get_data(self, msg):
        data = getattr(msg, self.attr)
        if self.separator:
            data += self.separator
        return data

    def get_logs_extra(self, msg):
        return {'msg_obj': msg}


class FileStorage(BaseFileStorage):
    name = 'File Storage'
    key = 'Filestorage'

    async def write_to_file(self, path, msg):
        self.log.debug('Writing to file %s', path)
        data = self.get_data(msg)
        async with FILE_OPENER(path, self.mode) as f:
            await f.write(data)
        self.log.debug('Data written to file %s', path)
        msg.processed()
        return path

    def do_one(self, msg):
        self.log.debug('Processing message for action %s', self.name)
        path = self.get_full_path(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        return self.write_to_file(path, msg)


class BufferedFileStorage(BaseFileStorage):
    name = 'Buffered File Storage'
    key = 'Bufferedfilestorage'

    configurable = BaseFileStorage.configurable.copy()
    configurable.update({'buffering': int, 'timeout': float})

    def __init__(self, *args, buffering=-1, timeout=5, **kwargs):
        super(BufferedFileStorage, self).__init__(*args, **kwargs)
        self.files = {}
        self.files_with_outstanding_writes = []
        self.buffering = buffering
        self.timeout = timeout

    def set_outstanding_writes(self, path):
        if path not in self.files_with_outstanding_writes:
            self.files_with_outstanding_writes.append(path)

    def get_file(self, path):
        self.log.debug('Getting file %s', path)
        try:
            return self.files[path]
        except KeyError:
            return ManagedFile(self.base_path, path, self.files, mode=self.mode, buffering=self.buffering,
                               timeout=self.timeout, logger=self.log, attr=self.attr, separator=self.separator)

    def write_to_file(self, path, msg):
        f = self.get_file(path)
        f.write(msg)
        self.set_outstanding_writes(path)

    def do_one(self, msg):
        self.log.debug('Storing message')
        path = self.get_path(msg)
        self.write_to_file(path, msg)

    def do_many(self, msgs):
        return self.do_many_sequential(msgs)

    async def wait_complete(self):
        try:
            self.log.debug('Waiting for outstanding writes to complete')
            self.log.debug(self.files_with_outstanding_writes)
            for path in self.files_with_outstanding_writes:
                f = self.get_file(path)
                await f.wait_writes_done()
            self.log.debug('All outstanding writes have been completed', extra=logs_extra)
        finally:
            self.files_with_outstanding_writes.clear()
            self.log.debug(self.files_with_outstanding_writes)

    async def close(self):
        files = list(self.files.values())
        for f in files:
            await f.close()
        i = 0
        while self.files and i < 20:
            await asyncio.sleep(0.1)
            i += 1
