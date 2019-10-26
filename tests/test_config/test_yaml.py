import yaml


class TestYamlConfig:
    def test_00_yaml_config_servers(self, config_file, expected_object, server_port_load,
                                    load_all_yaml_tags, server_pipe_address_load):
        server = yaml.safe_load(config_file)
        assert server.protocol_factory.preaction == expected_object.protocol_factory.preaction
        assert server.protocol_factory.action == expected_object.protocol_factory.action
        assert server.protocol_factory == expected_object.protocol_factory
        assert server == expected_object

    def test_01_yaml_config_server_with_logging(self, server_with_logging_yaml_config_stream, server_port_load,
                                                load_all_yaml_tags, tcp_server_one_way):
        server, misc_config = yaml.safe_load_all(server_with_logging_yaml_config_stream)
        assert server == tcp_server_one_way
