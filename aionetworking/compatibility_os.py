from __future__ import annotations
import signal
import asyncio
import os
from typing import Callable
try:
     from systemd import daemon
     from systemd import journal

     def send_to_journal(*args, **kwargs):
         journal.send(*args, **kwargs)

     def send_ready():
         daemon.notify('READY=1')

     def send_status(status: str):
         daemon.notify(f'STATUS={status}')

     def send_stopping():
         daemon.notify('STOPPING=1')

     def send_reloading():
        daemon.notify('RELOADING=1')
except ImportError:
    def send_to_journal(*args, **kwargs): ...

    def send_ready():
        pass

    def send_status(status: str):
        pass

    def send_stopping():
        pass

    def send_reloading():
        pass


def loop_on_user1_signal(callback: Callable):
    if os.name == 'posix':
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGUSR1, callback)


def loop_on_close_signal(callback: Callable):
    if os.name == 'posix':
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, callback)
        loop.add_signal_handler(signal.SIGINT, callback)


def loop_remove_signals():
    if os.name == 'posix':
        loop = asyncio.get_event_loop()
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGUSR1)


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
