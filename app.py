from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib.run_receiver import main
from lib.utils import set_loop
import definitions

import asyncio
import argparse
import os


definitions.PROTOCOLS = {
    'TCAP': TCAP_MAP_ASNProtocol
}


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conffile', help='Path to config ini file')

    args = parser.parse_args()

    conf_file = args.conffile or os.environ['MESSAGE_MANAGER_CONF_FILE'] or os.path.join(definitions.CONF_DIR,
                                                                                         'setup_devel.ini')

    return conf_file


def get_configuration_args(config_file=None):
    if not config_file:
        config_file = process_args()
    return config_file,


if __name__ == '__main__':
    set_loop()
    definitions.CONFIG_ARGS = get_configuration_args()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
