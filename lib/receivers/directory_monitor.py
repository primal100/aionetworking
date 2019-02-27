import asyncio
import time
from pathlib import Path
from lib.receivers import BaseReceiver


class DirectoryMonitor(BaseReceiver):
    configurable = {'directory': Path, 'glob': str, 'scan_interval': int, 'check_finished': int, 'recursive': bool,
                    'remove_after_processing': bool}

    def __init__(self, *args, directory, glob=None, rglob=None, scan_interval=0, check_finished=0.1,
                 remove_after_processing:bool = True, **kwargs):
        super(DirectoryMonitor, self).__init__(*args, **kwargs)
        self.method = directory.rglob if rglob else directory.glob if glob else directory.iterdir
        self.args = (rglob,) if rglob else (glob,) if glob else ()
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.scan_interval = scan_interval
        self.check_finished = check_finished
        self.mode = 'rb' if self.manager.protocol.binary else 'r'
        self.remove_after_processing = remove_after_processing
        self.tasks = {}

    async def close(self):
        await asyncio.wait(self.tasks)

    def delete_task(self, future):
        path = future.result()
        del self.tasks[str(path)]

    async def process_file(self, path):
        self.logger.debug('Found file %s', path)
        while time.time() - path.stat.st_mtime < self.check_finished:
            await asyncio.sleep(self.check_finished)
        with path.open(mode=self.mode):
            data = path.read()
        self.manager.handle_message(path.owner(), data)
        if self.remove_after_processing:
            path.unlink()
        return path

    async def run(self):
        while True:
            for path in self.method(*self.args):
                task = asyncio.create_task(self.process_file(path))
                self.tasks[str(path)] = task
                task.add_done_callback(self.delete_task)
            await asyncio.sleep(self.scan_interval)



