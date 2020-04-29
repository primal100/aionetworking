#!/usr/bin/env python
from aionetworking.runners import run_server_default_tags
from aionetworking.utils import set_loop_policy


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('conf', type=str, nargs='?',
                        help='Path to .yaml config file')
    parser.add_argument('-t', '--timeout', default=None, type=int,
                        help='stop the server after this time')
    parser.add_argument('-l', '--loop', default=None, type=str,
                        help='loop to use')
    parser.add_argument('-p', '--notify-pid', type=int,
                        help='pid of process to send USRSIG2 to when server is started')
    args, kw = parser.parse_known_args()
    if args.loop:
        set_loop_policy(posix_loop_type=args.loop, windows_loop_type=args.loop)
    run_server_default_tags(args.conf, notify_pid=args.notify_pid, timeout=args.timeout)
