from tests.test_senders.conftest import *


@pytest.fixture
def echo_exception_response_encoded() -> bytes:
    return b'{"id": 2, "error": "InvalidRequestError"}'


@pytest.fixture
def echo_exception_response() -> dict:
    return {'id': 2, 'error': 'InvalidRequestError'}


@pytest.fixture
def echo_exception_response_object(echo_exception_response_encoded, echo_exception_response) -> JSONObject:
    return JSONObject(echo_exception_response_encoded, echo_exception_response)
