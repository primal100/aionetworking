from tests.test_08_config.conftest import *
import pytest
from scripts import sample_server
from concurrent.futures import ThreadPoolExecutor


@pytest.fixture
def sample_server_script() -> str:
    return sample_server.__file__


@pytest.fixture(scope='session')
def executor() -> ThreadPoolExecutor:
    executor = ThreadPoolExecutor()
    yield executor
    executor.shutdown(wait=True)

