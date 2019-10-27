import logging
from lib.conf.yaml_config import node_from_config


class TestYamlConfig:
    def test_00_yaml_config_node(self, config_file, expected_object, all_paths, load_all_yaml_tags, reset_logging):
        node = node_from_config(config_file, paths=all_paths)
        assert node == expected_object

    def test_01_yaml_config_node_with_logging(self, config_file_logging, expected_object_logging, all_paths,
                                              load_all_yaml_tags, peer_filter, reset_logging):
        node = node_from_config(config_file_logging, paths=all_paths)
        assert node == expected_object_logging
        root_logger = logging.getLogger()
        assert root_logger.getEffectiveLevel() == logging.INFO
        assert root_logger.propagate is True
        assert len(root_logger.handlers) == 2
        receiver_logger = logging.getLogger('receiver')
        assert receiver_logger.getEffectiveLevel() == logging.INFO
        sender_logger = logging.getLogger('sender')
        assert sender_logger.getEffectiveLevel() == logging.INFO
        receiver_connection_logger = logging.getLogger('receiver.connection')
        assert receiver_connection_logger.getEffectiveLevel() == logging.INFO
        sender_connection_logger = logging.getLogger('sender.connection')
        assert sender_connection_logger.getEffectiveLevel() == logging.INFO
        receiver_stats_logger = logging.getLogger('receiver.stats')
        assert receiver_stats_logger.getEffectiveLevel() == logging.INFO
        sender_stats_logger = logging.getLogger('sender.stats')
        assert sender_stats_logger.getEffectiveLevel() == logging.INFO
        receiver_raw_logger = logging.getLogger('receiver.raw_received')
        assert receiver_raw_logger.filters == [peer_filter]
        assert receiver_raw_logger.getEffectiveLevel() == logging.DEBUG
        sender_raw_logger = logging.getLogger('sender.raw_sent')
        assert sender_raw_logger.getEffectiveLevel() == logging.DEBUG
        assert sender_raw_logger.filters == [peer_filter]
        receiver_msg_logger = logging.getLogger('receiver.msg_received')
        assert receiver_msg_logger.getEffectiveLevel() == logging.DEBUG
        sender_msg_logger = logging.getLogger('sender.msg_sent')
        assert sender_msg_logger.getEffectiveLevel() == logging.DEBUG
        loggers = [receiver_logger, sender_logger, receiver_connection_logger, sender_connection_logger,
                   receiver_stats_logger, sender_stats_logger, receiver_raw_logger, sender_raw_logger,
                   receiver_msg_logger, sender_msg_logger]
        for logger in loggers:
            assert logger.propagate is False
            assert len(logger.handlers) == 2
