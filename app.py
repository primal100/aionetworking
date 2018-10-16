from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import binary, decode, prettify, summarise, text
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.configuration.parser import ConfigParserFile
from lib.run import main
import definitions

import asyncio
import argparse
import os


app_name = 'message_receiver'


receivers = {
    'TCPServer': {'receiver': TCPServerReceiver, 'sender': TCPClient},
    'UDPServer': {'receiver': UDPServerReceiver, 'sender': UDPClient}
}


actions = {
    'binary': binary,
    'decode': decode,
    'prettify': prettify,
    'summarise': summarise,
    'text': text
}

protocols = {
    'TCAP': TCAP_MAP_ASNProtocol
}


def get_config_files(conf_dir=None, configfile=None, log_config_file=None, logfilename='logging.ini'):
    if not configfile:
            configfile = os.path.join(conf_dir, 'setup.ini')
    if not log_config_file:
            log_config_file = os.path.join(conf_dir, logfilename)

    config_meta = {
        'filename': configfile
        }

    return ConfigParserFile(config_meta), log_config_file


def process_args(config_dir=definitions.CONF_DIR, logfilename='logging.ini'):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--confdir', help='Path to setup.ini and logging.ini', default=config_dir)
    parser.add_argument('-f', '--config', help='Path to configparser setup file')
    parser.add_argument('-l', '--logconfig', help='Path to logconfig file')

    args = parser.parse_args()

    return get_config_files(conf_dir=args.confdir, configfile=args.config, log_config_file=args.logconfig,
                            logfilename=logfilename)


if __name__ == '__main__':
    configuration, log_config_path = process_args()
    try:
        asyncio.run(main(app_name, receivers, actions, protocols, configuration, log_config_path))
    except KeyboardInterrupt:
        pass
