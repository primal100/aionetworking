import asyncio
from pathlib import Path

from lib.conf import RawStr
from lib.settings import FILE_OPENER
from lib import settings


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

    async def write(self, data):
        await self.queue.put(data)

    def close(self):
        await self.queue.join()
        self.task.cancel()

    def cleanup(self):
        del self.files_dict[self.path]

    async def manage(self):
        async with FILE_OPENER(self.full_path, mode=self.mode, buffering=self.buffering) as f:
            try:
                while True:
                    data = await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
                    num = 1
                    while not self.queue.empty():
                        try:
                            data += self.queue.get_nowait()
                            num += 1
                        except asyncio.QueueEmpty:
                            break
                    await f.write(data)
                    for i in range(0, num):
                        self.queue.task_done()
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                pass
            finally:
                self.cleanup()


class BaseFileStorage:

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
    as_task = True

    async def write_to_file(self, path, data):
        async with settings.FILE_OPENER(path, self.mode) as f:
            await f.write(data)

    async def process(self, msg):
        path = self.get_full_path(msg)
        data = self.get_data(msg)
        await self.write_to_file(path, data)
        return path


class BufferedFileStorage(BaseFileStorage):
    as_task = False
    files = {}

    configurable = BaseFileStorage.configurable.copy()
    configurable.update({'buffering': int, 'timeout': float})

    def __init__(self, *args, buffering=-1, timeout=5):
        super(BufferedFileStorage, self).__init__(*args)
        self.buffering = buffering
        self.timeout = timeout

    def get_file(self, path):
        try:
            return self.files[path]
        except KeyError:
            return ManagedFile(self.base_path, path, self.files, mode=self.mode, buffering=self.buffering,
                               timeout=self.timeout)

    async def write_to_file(self, path, data):
        f = self.get_file(path)
        await f.write(data)

    async def process(self, msg):
        path = self.get_path(msg)
        data = self.get_data(msg)
        await self.write_to_file(path, data)


