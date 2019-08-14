from dataclasses import asdict
import pickle


class TestLogger:
    def test_00_init(self, receiver_logger):
        assert receiver_logger.logger.name == 'receiver.logger'
        assert receiver_logger.extra == ''
        assert receiver_logger.datefmt == '%Y-%M-%d %H:%M:%S'

    def test_01_process(self, receiver_logger): ...

    def test_02_manage_error(self, receiver_logger, caplog) -> None: ...

    def test_03_manage_critical_error(self, receiver_logger, caplog) -> None: ...

    def test_04_log_num_connections(self, receiver_logger, caplog): ...

    def test_05_get_connection_logger(self, receiver_logger, receiver_connection_logger): ...

    def test_06_as_dict(self, receiver_logger):
        d = asdict(receiver_logger)
        assert d == {'logger_name': 'receiver', 'datefmt': '%Y-%M-%d %H:%M:%S', 'extra': {}}

    def test_07_pickle(self, receiver_logger):
        p = pickle.dumps(receiver_logger, protocol=4)
        logger = pickle.loads(p)
        assert receiver_logger == logger

    def test_08_pickle_is_closing(self, receiver_logger):
        receiver_logger._set_closing()
        p = pickle.dumps(receiver_logger, protocol=4)
        logger = pickle.loads(p)
        assert receiver_logger == logger
