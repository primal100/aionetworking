import argparse
import os
from pathlib import Path

import settings


def process_args(devel: bool=False) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conffile', help='Path to config ini file')

    args = parser.parse_args()

    conffile = args.conffile or os.environ.get('MESSAGE_MANAGER_CONF_FILE', '')

    if conffile:
        conf_file = Path(args.conffile)
    elif devel:
        conf_file = settings.CONF_DIR.joinpath('setup_devel.ini')
    else:
        conf_file = settings.CONF_DIR.joinpath('setup.ini')

    return conf_file


def get_configuration_args(config_file: Path=None) -> tuple:
    if not config_file:
        config_file = process_args()
    return config_file,

