import yaml


class TestYamlConfig:
    def test_00_yaml_config_servers(self, config_file, expected_object, server_port_load, tmpdir,
                                    load_all_yaml_tags, load_tmp_dir_tag, load_ssl_dir_tag, server_pipe_address_load):
        server = yaml.safe_load(config_file)
        assert server.protocol_factory.action == expected_object.protocol_factory.action
        assert server.protocol_factory.preaction == expected_object.protocol_factory.preaction
        assert server.protocol_factory == expected_object.protocol_factory
        assert server == expected_object
