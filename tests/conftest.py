from __future__ import annotations

import datetime
import os
import pytest
import freezegun
from aionetworking.utils import set_loop_policy


def pytest_addoption(parser):
    default = 'proactor' if os.name == 'nt' else 'selector'
    choices = ('selector', 'uvloop') if os.name == 'linux' else ('proactor', 'selector')
    parser.addoption(
        "--loop",
        action="store",
        default=default,
        help=f"Loop to use. Choices are: {','.join(choices)}",
    )


def pytest_configure(config):
    loop_type = config.getoption("--loop")
    if loop_type:
        set_loop_policy(linux_loop_type=loop_type, windows_loop_type=loop_type)


def get_fixture(request, param=None):
    if not param:
        param = request.param
    return request.getfixturevalue(param.__name__)


@pytest.fixture
def timestamp() -> datetime.datetime:
    return datetime.datetime(2019, 1, 1, 1, 1)


@pytest.fixture
def fixed_timestamp(timestamp) -> datetime.datetime:
    freezer = freezegun.freeze_time(timestamp)
    freezer.start()
    yield datetime.datetime.now()
    freezer.stop()