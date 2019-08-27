from tests.test_senders.conftest import *


@pytest.fixture
def protocol_factory_one_way_server_benchmark(buffered_file_storage_action, initial_server_context,
                                              receiver_logger) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    logger_cv.set(receiver_logger)
    factory = StreamServerProtocolFactory(
        action=buffered_file_storage_action,
        dataformat=JSONObject,
        logger=receiver_logger)
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory


@pytest.fixture
async def tcp_server_one_way_benchmark(protocol_factory_one_way_server_benchmark, receiver_logger, sock):
    server = TCPServer(protocol_factory=protocol_factory_one_way_server_benchmark, host=sock[0],
                       port=8886)
    await server.start()
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
def tcp_client_one_way(protocol_factory_one_way_client, sock, peername):
    return TCPClient(protocol_factory=protocol_factory_one_way_client, host=sock[0], port=8886, srcip=peername[0],
                     srcport=0)

