#!/usr/bin/env python
from pathlib import Path
import asyncssh
from typing import Union


def generate_key_in_path(path: Union[Path, str], alg_name='ssh-rsa'):
    skey = asyncssh.generate_private_key(alg_name)
    skey.write_private_key(str(path))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(type=Path, dest='path',
                        help='path to file to store the ssh key')
    parser.add_argument('--algorithm', default='ssh-rsa', type=str,
                        help='algorithim to use to generate the key')
    p = parser.parse_args()
    generate_key_in_path(p.path, p.algorithm)