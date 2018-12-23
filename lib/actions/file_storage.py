import asyncio
from pathlib import Path

from lib.conf import RawStr
from lib.settings import FILE_OPENER, get_logger
from lib import settings


logger = get_logger('actions')


class ManagedFile:
    f = None

    def __init__(self, base_path, path, files_dict, mode='ab', buffering=-1, timeout=5):
        self.full_path = base_path.joinpath(path)
        self.path = path
        self.files_dict[path] = self
        self.mode = mode
        self.buffering = buffering
        self.timeout = timeout
        self.files_dict = files_dict
        self.files_dict[path] = self
        self.queue = asyncio.Queue()
        self.task = asyncio.create_task(self.manage())

    async def write(self, data, **logs_extra):
        logger.debug('Adding to write queue for file %s', self.path, extra=logs_extra)
        await self.queue.put(data)
        logger.debug('Added to write queue for file %s', self.path, extra=logs_extra)

    def close(self):
        logger.debug('Closing file %s', self.path)
        await self.wait_writes_done()
        self.task.cancel()
        logger.debug('Closed file %s', self.path)

    def cleanup(self):
        del self.files_dict[self.path]
        logger.debug('Cleanup completed for %s', self.path)

    async def wait_writes_done(self, **logs_extra):
        logger.debug('Waiting for writes to complete for %s', self.path, extra=logs_extra)
        await self.queue.join()
        logger.debug('Writes completed for %s', self.path, extra=logs_extra)

    async def manage(self):
        logger.info('Opening file %s', self.path)
        async with FILE_OPENER(self.full_path, mode=self.mode, buffering=self.buffering) as f:
            try:
                while True:
                    logger.debug('Retrieving item from queue for file %s', self.path)
                    data = await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
                    num = 1
                    while not self.queue.empty():
                        try:
                            data += self.queue.get_nowait()
                            num += 1
                        except asyncio.QueueEmpty:
                            logger.info('QueueEmpty error was caught for file %s', self.path)
                    logger.debug('Retrieved %s items from queue. Writing on file %s.', num, self.path)
                    await f.write(data)
                    logger.debug('Data written for file %s', self.path)
                    for i in range(0, num):
                        self.queue.task_done()
                    logger.debug('Task done set for %s items on file', num, self.path)
            except asyncio.TimeoutError:
                logger.info('File %s closing due to timeout', self.path)
            except asyncio.CancelledError:
                logger.info('File %s closing due to task being cancelled', self.path)
            finally:
                self.cleanup()


class BaseFileStorage:
    action_type = ''

    configurable = {
        'base_path': Path,
        'path': RawStr,
        'attr': str,
        'mode': str,
        'separator': str
    }

    @classmethod
    def from_config(cls, **kwargs):
        config = settings.CONFIG.section_as_dict('FileStorage', **cls.configurable)
        logger.debug('Found configuration for %s:%s', cls.action_type, config)
        config.update(kwargs)
        return cls(**config)

    def __init__(self, base_path, path, attr, mode='w', separator=None):
        self.base_path = base_path
        self.path = path
        self.attr = attr
        self.mode = mode
        self.separator = separator

    def get_full_path(self, msg):
        return self.base_path.joinpath(self.get_path(msg))

    def get_path(self, msg):
        return self.path.format(msg=msg)

    def get_data(self, msg):
        data = getattr(msg, self.attr)
        if self.separator:
            data += self.separator
        return data


class FileStorage(BaseFileStorage):
    action_type = 'File Storage'
    as_task = True

    async def write_to_file(self, path, data, **logs_extra):
        logger.debug('Writing to file %s', path, extra=logs_extra)
        async with settings.FILE_OPENER(path, self.mode) as f:
            await f.write(data)
        logger.debug('Data written to file %s', path, extra=logs_extra)

    async def process(self, msg):
        logger.debug('Processing message for action %s', self.action_type, extra={'msg': msg})
        path = self.get_full_path(msg)
        data = self.get_data(msg)
        await self.write_to_file(path, data)
        return path


class BufferedFileStorage(BaseFileStorage):
    action_type = 'Buffered File Storage'
    as_task = False
    files = {}
    files_with_outstanding_writes = []

    configurable = BaseFileStorage.configurable.copy()
    configurable.update({'buffering': int, 'timeout': float})

    def __init__(self, *args, buffering=-1, timeout=5):
        super(BufferedFileStorage, self).__init__(*args)
        self.buffering = buffering
        self.timeout = timeout

    def set_outstanding_writes(self, path):
        if path not in self.files_with_outstanding_writes:
            self.files_with_outstanding_writes.append(path)

    def get_file(self, path, **logs_extra):
        logger.debug('Getting file %s', path, extra=logs_extra)
        try:
            return self.files[path]
        except KeyError:
            return ManagedFile(self.base_path, path, self.files, mode=self.mode, buffering=self.buffering,
                               timeout=self.timeout)

    async def write_to_file(self, path, data, **logs_extra):
        f = self.get_file(path, **logs_extra)
        await f.write(data, **logs_extra)
        self.set_outstanding_writes(path)

    async def process(self, msg):
        logger.debug('Storing message', extra={'msg':msg})
        path = self.get_path(msg)
        data = self.get_data(msg)
        await self.write_to_file(path, data, msg=msg)

    async def wait_complete(self, **logs_extra):
        logger.debug('Waiting for outstanding writes to complete', extra=logs_extra)
        for path in self.files_with_outstanding_writes:
            f = self.get_file(path)
            await f.wait_writes_done()
        self.files_with_outstanding_writes = []
        logger.debug('All outstanding writes have been completed', extra=logs_extra)
