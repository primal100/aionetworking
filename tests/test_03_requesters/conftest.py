from tests.test_02_actions.conftest import *
from aionetworking.requesters import EchoRequester
import pytest


@pytest.fixture
def echo_requester() -> EchoRequester:
    return EchoRequester()



