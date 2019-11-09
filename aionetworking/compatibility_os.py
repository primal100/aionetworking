from __future__ import annotations
import signal
import threading
import asyncio
import os
from typing import Callable
try:
     from systemd.daemon import notify
     from systemd import journal

     def send_to_journal(*args, **kwargs):
         journal.send(*args, **kwargs)

     def send_ready():
         notify('READY=1')

     def send_status(status: str):
         notify(f'STATUS={status}')

     def send_stopping():
         notify(f'STOPPING=1')

     def send_reloading():
        notify(f'RELOADING=1')
except ImportError:
    def send_to_journal(*args, **kwargs): ...

    def send_ready(): ...


    def send_status(status: str): ...


    def send_stopping(): ...


    def send_reloading(): ...


def loop_on_user1_signal(callback: Callable):
    if os.name == 'posix':
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGUSR1, callback)


def on_close_signal_posix(callback: Callable):
    def handler(signum, frame):
        callback()
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def loop_on_close_signal(callback: Callable):
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, callback)
    loop.add_signal_handler(signal.SIGINT, callback)


def loop_remove_signals():
    if os.name == 'posix':
        loop = asyncio.get_event_loop()
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGUSR1)


async def wait_event(event: threading.Event):
    await asyncio.get_event_loop().run_in_executor(None, event.wait)


def wait_event_in_loop(event):
    """
    Best way to catch ctrl +c in Windows is with Asyncio ProactorEventLoop in Python3.8
    """
    asyncio.run(wait_event(event))


def wait_close_signal():
    event = threading.Event()
    if os.name == 'posix':
        on_close_signal_posix(event.set)
        event.wait()
    else:
        try:
            wait_event_in_loop(event)
        except KeyboardInterrupt:
            event.set()


if os.name == 'posix':
    import pamela
    authentication_type = 'PAM'

    def authenticate(username: str, password: str, pam_service: str = 'sftplogin', **kwargs) -> bool:
        try:
            pamela.authenticate(username, password, pam_service)
            return True
        except pamela.PAMError:
            return False
elif os.name == 'nt':
    import pywintypes
    import win32security
    import win32con

    authentication_type = 'WINDOWS'

    def authenticate(username: str, password: str, domain: str = '.', logon_type=win32con.LOGON32_LOGON_BATCH,
                     logon_provider=win32con.LOGON32_PROVIDER_DEFAULT, **kwargs) -> bool:
        try:
            win32security.LogonUser(username, domain, password, logon_type, logon_provider)
            return True
        except pywintypes.error:
            return False
