import asyncio
import datetime
import os
import time

from pathlib import Path
from lib.counters import TaskCounter
from lib.receivers import BaseReceiver
from lib.utils import log_exception


class DirectoryMonitor(BaseReceiver):
    configurable = {'directory': Path, 'glob': str, 'rglob': str, 'scan_interval': int,
                    'check_finished': int, 'sort': str, 'concatenate': bool, 'timeout': int}

    def __init__(self, *args, directory, glob=None, rglob=None, scan_interval=0.005, check_finished=0.1,
                 sort: str = None, timeout: int = 5, concatenate = False, remove_tmp_files: bool = False,**kwargs):
        super(DirectoryMonitor, self).__init__(*args, **kwargs)
        self.method = directory.rglob if rglob else directory.glob if glob else directory.iterdir
        self.args = (rglob,) if rglob else (glob,) if glob else ()
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.scan_interval = scan_interval
        self.check_finished = check_finished
        self.mode = 'rb' if self.manager.protocol.binary else 'r'
        self.sort = sort
        self.concatenate = concatenate
        self.remove_tmp_files = remove_tmp_files
        self.timeout = timeout
        self.task_counter = TaskCounter()
        self.tasks = {}

    async def close(self):
        await self.task_counter.wait()
        await self.run_once()
        self.logger.debug('%s waiting for tasks to complete', self.receiver_type)
        try:
            await asyncio.wait_for(self.task_counter.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            self.logger.error('Directory Monitor closed with %s tasks remaining', self.task_counter.num)

    def get_sender(self, path):
        if os.name == 'posix':
            return path.owner()
        return ''

    async def process_file(self, path):
        self.logger.debug('Found file %s', path)
        stat = None
        while not stat or (time.time() - stat.st_mtime < self.check_finished):
            try:
                stat = path.stat()
            except FileNotFoundError:
                stat = None
            await asyncio.sleep(self.check_finished)
        data = None
        while not data:
            try:
                with path.open(mode=self.mode) as f:
                    data = f.read()
            except FileNotFoundError:
                pass
            await asyncio.sleep(self.check_finished)
        return {'path': path, 'ctime': stat.st_ctime, 'data': data}

    def find(self):
        for path in self.method(*self.args):
            yield path

    def sort_files(self, files):
        if self.sort == 'created':
            return sorted(files, key=lambda x: x['ctime'])
        elif self.sort == 'filename':
            return sorted(files, key=lambda x: x['path'])
        else:
            return files

    def manage_errors(self, *exceptions):
        for exc in exceptions:
            if exc:
                self.logger.error(log_exception(exc))

    def remove_processed_files(self, files):
        if self.remove_tmp_files:
            for path in files:
                self.logger.debug('Removing file %s', path)
                path.unlink()

    async def concatenate_files(self, files):
        self.logger.debug('Concatenating files: %s', [f['path'] for f in files])
        data = b'' if self.mode == 'rb' else ''
        for f in files:
            data += f['data']
        first = files[0]
        timestamp = datetime.datetime.fromtimestamp(first['ctime'])
        await self.manager.handle_message(self.get_sender(first), data, timestamp=timestamp)

    async def run_once(self):
        tasks = []
        for path in self.find():
            tasks.append(self.task_counter.create_task(self.process_file(path)))
        completed, pending = await asyncio.wait(tasks)
        files = self.sort_files([t.result() for t in completed])
        if self.concatenate:
            await self.concatenate_files(files)
        else:
            self.logger.debug('Handling files: %s', [f['path'] for f in files])
            tasks = []
            for f in files:
                timestamp = datetime.datetime.fromtimestamp(f['ctime'])
                tasks.append(self.manager.handle_message(self.get_sender(f['path']), f['data'], timestamp=timestamp))
            completed, pending = await asyncio.wait(tasks)
            exceptions = [t.exception() for t in completed]
            self.manage_errors(*exceptions)
        self.remove_processed_files(f['path'] for f in files)

    async def run(self):
        while True:
            await self.task_counter.wait()
            await asyncio.sleep(self.scan_interval)
            await self.run_once()




