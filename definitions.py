import os
from pathlib import Path, PurePath
from lib.conf.parser import INIFileConfig
from lib.messagemanagers.messagemanager import MessageManager
from lib.messagemanagers.batchmessagemanager import BatchMessageManager
from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.receivers.sftp import SFTPServerPswAuth
from lib.senders.sftp import SFTPClient
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import binary, decode, prettify, summarise, text

APP_NAME = 'Message Manager'
ROOT_DIR = Path.resolve(__file__).parent
CONF_DIR = ROOT_DIR.joinpath('conf')
LOGS_DIR = ROOT_DIR.joinpath('logs')
DATA_DIR = ROOT_DIR.joinpath('data')
RECORDINGS_DIR = ROOT_DIR.joinpath('recordings')
TESTS_DIR = ROOT_DIR.joinpath('tests')
TEST_CONF_DIR = TESTS_DIR.joinpath('conf')
TEST_LOGS_DIR = TESTS_DIR.joinpath('logs')
TEST_DATA_DIR = TESTS_DIR.joinpath('data')
TEST_RECORDINGS_DIR = TEST_DATA_DIR.joinpath('recordings')
USER_HOME = Path.home()
OSDATA_DIR = PurePath(os.environ.get('appdata', USER_HOME), APP_NAME)
OSDATA_CONF_DIR = OSDATA_DIR.joinpath('conf')
OSDATA_DATA_DIR = OSDATA_DIR.joinpath('data')
OSDATA_LOGS_DIR = OSDATA_DIR.joinpath('logs')
OSDATA_RECORDINGS_DIR = OSDATA_DIR.joinpath('recordings')
HOME = OSDATA_DIR
LOGGER_NAME = 'receiver'
POSTFIX = 'receiver'
CONFIG = None
CONFIG_CLS = INIFileConfig
CONFIG_ARGS = CONF_DIR.joinpath("setup.ini"),
RECEIVERS = {
    'TCPServer': {'receiver': TCPServerReceiver, 'sender': TCPClient},
    'UDPServer': {'receiver': UDPServerReceiver, 'sender': UDPClient},
    'SFTPServer':  {'receiver': SFTPServerPswAuth, 'sender': SFTPClient},
}
ACTIONS = {
    'binary': binary,
    'decode': decode,
    'prettify': prettify,
    'summarise': summarise,
    'text': text
}
MESSAGE_MANAGER = MessageManager
BATCH_MESSAGE_MANAGER = BatchMessageManager
PROTOCOLS = {}
