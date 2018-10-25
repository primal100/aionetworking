from lib.utils import set_loop
from lib.conf.parser import INIFileConfig
from lib.run_sender import get_sender
from lib.senders.tasks import send_hex, encode_send_msg, play_recording
import definitions

import argparse
import asyncio
from pathlib import PurePath
import os

set_loop()


def process_args(devel=False):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conffile', help='Path to config ini file')
    parser.add_argument('-s', '--sendhex', help='Send hex data')
    parser.add_argument('-e', '--sendencoded', help='Encode and send')
    parser.add_argument('-p', '--playback', help='Playback given recording')

    args = parser.parse_args()

    conffile = args.conffile or os.environ.get('MESSAGE_MANAGER_CONF_FILE', '')

    if conffile:
        conf_file = PurePath(args.conffile)
    elif devel:
        conf_file = definitions.CONF_DIR.joinpath('setup_devel.ini')
    else:
        conf_file = definitions.CONF_DIR.joinpath('setup.ini')

    if args.sendencoded:
        task = encode_send_msg
        data = args.sendencoded
    elif args.playback:
        task = play_recording
        data = args.playback
    elif args.sendhex:
        task = send_hex
        data = args.sendhex
    else:
        task = data = None

    return conf_file, task, data


if __name__ == '__main__':
    conf_file, task, data = process_args()
    client = get_sender(app_name, receivers, protocols, *conf_file, config_cls=INIFileConfig)
    if task:
        asyncio.run(task(client, data))
        print('Message sent')
