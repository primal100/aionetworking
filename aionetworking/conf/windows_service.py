import asyncio
from aionetworking.runners import run_forever
from aionetworking.utils import set_loop_policy
import pywintypes
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket


class BaseAIONetworkingYamlService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AIONetworkingService"
    _svc_display_name_ = "AIONetworking Service"
    _svc_description_ = "AIONetworking Based Service"
    loop = 'proactor'
    conf_file = None
    paths = None

    def __init__(self, args):
        super().__init__(args)
        set_loop_policy(windows_loop_type=self.loop)
        self.task = None
        self.loop = None
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.loop.call_soon_threadsafe(self.task.cancel)

    def SvcDoRun(self):
        asyncio.run(self.main())

    async def main(self):
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.create_task(run_forever(self.conf_file, paths=self.paths))
        try:
            await self.task
        except asyncio.CancelledError:
            pass


