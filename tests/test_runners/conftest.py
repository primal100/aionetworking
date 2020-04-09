from tests.test_config.conftest import *
from concurrent.futures import ThreadPoolExecutor


@pytest.fixture(scope='session')
def executor() -> ThreadPoolExecutor:
    executor = ThreadPoolExecutor()
    yield executor
    executor.shutdown(wait=True)

