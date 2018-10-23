import os
from lib.conf.parser import INIFileConfig
from lib.messagemanagers.messagemanager import MessageManager
from lib.messagemanagers.batchmessagemanager import BatchMessageManager
from lib.receivers.asyncio_servers import TCPServerReceiver, UDPServerReceiver
from lib.receivers.sftp import SFTPServerPswAuth
from lib.senders.sftp import SFTPClient
from lib.senders.asyncio_clients import TCPClient, UDPClient
from lib.actions import binary, decode, prettify, summarise, text

APP_NAME = 'Message Manager'
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(ROOT_DIR, 'conf')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
TESTS_DIR = os.path.join(ROOT_DIR, 'tests')
TEST_CONF_DIR = os.path.join(TESTS_DIR, 'conf')
TEST_LOGS_DIR = os.path.join(TESTS_DIR, 'logs')
TEST_DATA_DIR = os.path.join(TESTS_DIR, 'data')
USER_HOME = os.path.expanduser("~")
OSDATA_DIR = os.environ.get('appdata', USER_HOME)
OSDATA_CONF_DIR = os.path.join(OSDATA_DIR, 'conf')
OSDATA_DATA_DIR = os.path.join(OSDATA_DIR, 'data')
OSDATA_LOGS_DIR = os.path.join(OSDATA_DIR, 'logs')
POSTFIX = 'receiver'
CONFIG = None
CONFIG_CLS = INIFileConfig
CONFIG_ARGS = os.path.join(CONF_DIR, "setup.ini"),
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