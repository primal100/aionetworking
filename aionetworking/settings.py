from __future__ import annotations
import os
from pathlib import Path
import aiofiles
import tempfile
import sys


APP_NAME = 'AIONetworking'
FILE_OPENER = aiofiles.open


def __getattr__(name):
    if name == 'TEMPDIR':
        return Path(tempfile.gettempdir()) / sys.modules[__name__].APP_NAME.replace(" ", "")
    elif name == 'APP_HOME':
        return Path(os.environ.get('appdata', Path.home()), sys.modules[__name__].APP_NAME)
