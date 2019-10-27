from __future__ import annotations
import sys


py38 = sys.version_info >= (3, 8)


if py38:
    from unittest.mock import AsyncMock
else:
    from asynctest.mock import CoroutineMock as AsyncMock
