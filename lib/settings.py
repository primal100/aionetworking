import logging
import os
from pathlib import Path
import aiofiles


APP_NAME = 'Message Manager'
ROOT_DIR = Path(__file__).parent.parent
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
OSDATA_DIR = Path(os.environ.get('appdata', USER_HOME), APP_NAME)
OSDATA_CONF_DIR = OSDATA_DIR.joinpath('conf')
OSDATA_DATA_DIR = OSDATA_DIR.joinpath('data')
OSDATA_LOGS_DIR = OSDATA_DIR.joinpath('logs')
OSDATA_RECORDINGS_DIR = OSDATA_DIR.joinpath('recordings')
HOME = OSDATA_DIR
LOGGER_NAME = 'app'
RAWDATA_LOGGER_NAME = 'rawdata'
POSTFIX = 'receiver'
CONFIG = None
CONFIG_ARGS = CONF_DIR.joinpath("setup.ini"),
#FILE_OPENER = aiofile.AIOFile
FILE_OPENER = aiofiles.open
