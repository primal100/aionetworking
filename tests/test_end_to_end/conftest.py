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


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_one_way_started.__name__, tcp_client_one_way.__name__,
         tcp_server_context.__name__, tcp_client_context.__name__)),
    pytest.param(
        lazy_fixture((udp_server_one_way_started.__name__, udp_client_one_way.__name__,
                      udp_server_context.__name__, udp_client_context.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way_started.__name__, pipe_client_one_way.__name__,
                      context_pipe_server.__name__, context_pipe_client.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections_in_other_process()")
    ),
    lazy_fixture(
        (sftp_server_started.__name__, sftp_client.__name__, sftp_server_context.__name__,
         sftp_client_context.__name__)),
])
def one_way_receiver_sender_args(request):
    return request.param


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_two_way_started.__name__, tcp_client_two_way.__name__)),
    lazy_fixture(
        (tcp_server_two_way_ssl_started.__name__, tcp_client_two_way_ssl.__name__)),
    pytest.param(
        lazy_fixture((udp_server_two_way_started.__name__, udp_client_two_way.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_two_way_started.__name__, pipe_client_two_way.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections_in_other_process()")
    )
])
def two_way_receiver_sender_args(request):
    return request.param


@pytest.fixture
def one_way_server_started(one_way_receiver_sender_args) -> BaseServer:
    return one_way_receiver_sender_args[0]


@pytest.fixture
def one_way_client(one_way_receiver_sender_args) -> BaseNetworkClient:
    return one_way_receiver_sender_args[1]


@pytest.fixture
def one_way_server_context(one_way_receiver_sender_args) -> Dict[str, Any]:
    return one_way_receiver_sender_args[2]


@pytest.fixture
def one_way_client_context(one_way_receiver_sender_args) -> Dict[str, Any]:
    return one_way_receiver_sender_args[3]


@pytest.fixture
def two_way_server_started(two_way_receiver_sender_args):
    return two_way_receiver_sender_args[0]


@pytest.fixture
def two_way_client(two_way_receiver_sender_args):
    return two_way_receiver_sender_args[1]

