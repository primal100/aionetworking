from app import app_name, receivers, get_configuration_args
from lib.configuration.parser import INIFileConfig
from lib.run_sender import get_sender

if __name__ == '__main__':
    config_args = get_configuration_args()
    client = get_sender(app_name, receivers, *config_args, config_cls=INIFileConfig)


