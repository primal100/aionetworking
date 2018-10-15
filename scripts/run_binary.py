from lib.receivers.asyncio_servers import TCPServer, UDPServer
from lib.actions import binary, decode, prettify, summarise
from lib.interfaces.contrib.TCAP_MAP import TCAP_MAP_ASNInterface
from lib.configuration.parser import ConfigParserFile
from lib.run import start
import definitions

import argparse
import os

app_name = 'binarymessagemanager'

receivers = {
    'TCPServer': TCPServer,
    'UDPServer': UDPServer
}

actions = {
    'binary': binary,
    'decode': decode,
    'prettify': prettify,
    'summarise': summarise
}

interfaces = {
    'TCAP': TCAP_MAP_ASNInterface
}

default_conf_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "conf")


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--confdir', help='Path to setup.ini and logging.ini', default=definitions.CONF_DIR)
    parser.add_argument('-f', '--config', help='Path to configparser setup file')
    parser.add_argument('-l', '--logconfig', help='Path to logconfig file')
    args = parser.parse_args()

    if not args.config:
            args.config = os.path.join(args.confdir, 'setup.ini')
    if not args.logconfig:
            args.logconfig = os.path.join(args.confdir, 'logging.ini')

    config_meta = {
        'filename': args.config
        }

    return ConfigParserFile(config_meta), args.logconfig


if __name__ == '__main__':
    config, log_config_path = process_args()
    start(app_name, receivers, actions, interfaces, config, log_config_path)

