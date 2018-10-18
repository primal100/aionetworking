from app import app_name, receivers, protocols, get_configuration_args, set_loop
from lib.configuration.parser import INIFileConfig
from lib.run_sender import get_sender

set_loop()

if __name__ == '__main__':
    config_args = get_configuration_args()
    client = get_sender(app_name, receivers, protocols, *config_args, config_cls=INIFileConfig)


