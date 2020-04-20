import os
from pathlib import Path
import aiofiles
import tempfile
import sys
from aionetworking.compatibility import py37


APP_NAME = 'AIONetworking'
FILE_OPENER = aiofiles.open
APP_CONFIG = {}


def __getattr__(name):
    path = None
    if name == 'TEMPDIR':
        path = Path(tempfile.gettempdir()) / sys.modules[__name__].APP_NAME.replace(" ", "")
    elif name == 'APP_HOME':
        path = Path(os.environ.get('appdata', Path.home()), sys.modules[__name__].APP_NAME)
    if path:
        path.mkdir(parents=True, exist_ok=True)
        return path


if not py37:
    from pep562 import Pep562
    Pep562(__name__)
