from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import binary, decode, prettify, summarise, text
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.configuration.parser import INIFileConfig
from lib.run_receiver import main
import definitions

import asyncio
import argparse
import os


app_name = 'message_manager'

config_cls = INIFileConfig

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


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conffile', help='Path to config ini file')

    args = parser.parse_args()

    conf_file = args.conffile or os.path.join(definitions.CONF_DIR, 'setup.ini')

    return conf_file


def get_configuration_args(config_file=None):
    if not config_file:
        config_file = process_args()
    return config_file,


if __name__ == '__main__':
    config_args = get_configuration_args()
    try:
        asyncio.run(main(app_name, receivers, actions, protocols, *config_args, config_cls=INIFileConfig))
    except KeyboardInterrupt:
        pass
