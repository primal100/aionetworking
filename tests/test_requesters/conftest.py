from tests.test_actions.conftest import *
from aionetworking.requesters.echo import EchoRequester
import pytest


@pytest.fixture
def echo_requester() -> EchoRequester:
    return EchoRequester()



