from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.actions import binary, decode, prettify, summarise
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.configuration.parser import ConfigParserFile
from lib.run import main
import asyncio
import definitions

import argparse
import os

loop = asyncio.ProactorEventLoop()
asyncio.set_event_loop(loop)

app_name = 'binarymessagemanager'

receivers = {
    'TCPServer': TCPServerReceiver,
    'UDPServer': UDPServerReceiver
}

actions = {
    'binary': binary,
    'decode': decode,
    'prettify': prettify,
    'summarise': summarise
}

protocols = {
    'TCAP': TCAP_MAP_ASNProtocol
}


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
    try:
        asyncio.run(main(app_name, receivers, actions, protocols, config, log_config_path))
    except KeyboardInterrupt:
        pass
