import asyncio
import os
import time

from pathlib import Path
from lib.counters import TaskCounter
from lib.receivers import BaseReceiver


class DirectoryMonitor(BaseReceiver):
    configurable = {'directory': Path, 'glob': str, 'rglob': str, 'scan_interval': int,
                    'check_finished': int, 'timeout': int}

    def __init__(self, *args, directory, glob=None, rglob=None, scan_interval=0.005, check_finished=0.1,
                 timeout: int = 5, **kwargs):
        super(DirectoryMonitor, self).__init__(*args, **kwargs)
        self.method = directory.rglob if rglob else directory.glob if glob else directory.iterdir
        self.args = (rglob,) if rglob else (glob,) if glob else ()
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.scan_interval = scan_interval
        self.check_finished = check_finished
        self.mode = 'rb' if self.manager.protocol.binary else 'r'
        self.timeout = timeout
        self.task_counter = TaskCounter()
        self.lock = asyncio.Lock()
        self.tasks = {}

    async def close(self):
        await self.task_counter.wait()
        self.run_once()
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
        self.manager.handle_message(self.get_sender(path), data)
        self.logger.debug('Removing file %s', path)
        path.unlink()
        return path

    def find(self):
        for path in self.method(*self.args):
            yield path

    def run_once(self):
        for path in self.find():
            self.task_counter.create_task(self.process_file(path))

    async def run(self):
        while True:
            print('scanning sleep for %s' % self.scan_interval)
            await self.task_counter.wait()
            await asyncio.sleep(self.scan_interval)
            print('scanning sleep done')
            self.run_once()




