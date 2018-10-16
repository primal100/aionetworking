from app import receivers, process_args
import os
import logging
from logging.config import fileConfig


def get_client(configuration, log_config_path):
    logging_setup = False
    while not logging_setup:
        try:
            fileConfig(log_config_path)
            logging_setup = True
        except FileNotFoundError as e:
            log_directory = os.path.dirname(e.filename)
            os.makedirs(log_directory, exist_ok=True)

    logger = logging.getLogger()
    logger.info('Starting client')
    logger.debug('Using logging config file %s' % log_config_path)
    client_cls = receivers[configuration.receiver]['sender']
    return client_cls.from_config(configuration.receiver_config)


if __name__ == '__main__':
    configuration, log_config_path = process_args(logfilename='logging_client.ini')
    client = get_client(configuration, log_config_path)

