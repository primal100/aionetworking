import configparser
import logging
from unittest import TestCase

from lib.conf.parser import INIFileConfig
from lib.protocols.contrib.TCAP_MAP import TCAP_MAP_ASNProtocol
from lib import definitions, settings

from pathlib import Path
from typing import AnyStr

settings.LOGGER_NAME = 'messagemanager'
settings.DATA_DIR = settings.TEST_DATA_DIR
settings.CONFIG_ARGS = settings.TEST_CONF_DIR.joinpath('tcp_server_test_setup.ini'),
definitions.PROTOCOLS = {'TCAP': TCAP_MAP_ASNProtocol}

logger = logging.getLogger(settings.LOGGER_NAME)
logger.setLevel(logging.CRITICAL)


class BaseTestCase(TestCase):
    maxDiff = None
    log_level = logging.CRITICAL
    base_data_dir = settings.TEST_DATA_DIR
    base_recordings_dir = settings.TEST_RECORDINGS_DIR

    async def do_async(self, func, *args):
        await func(*args)

    def enable_logging(self):
        logger.setLevel(self.log_level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    def prepare_config(self):
        config = configparser.ConfigParser()
        config.add_section('Receiver')
        config.add_section('MessageManager')
        config.add_section('Protocol')
        config.add_section('Actions')
        config.add_section('Print')
        config.add_section('Aliases')
        config.set('MessageManager', 'Batch', 'False')
        config.set('MessageManager', 'AllowedSenders', '10.10.10.10')
        config.set('MessageManager', 'GenerateTimestamp', 'False')
        config.set('Protocol', 'Name', 'TCAP')
        config.set('Actions', 'Home', self.base_data_dir)
        config.set('Actions', 'Types', 'binary,decode,prettify,summarise')
        config.set('Print', 'Types', 'binary,decode,prettify,summarise')
        return INIFileConfig()

    def assertFileContentsEqual(self, file_path: Path, expected_contents: AnyStr, mode: str='r'):
        self.assertTrue(file_path.exists(), msg='%s does not exist' % file_path)
        with file_path.open(mode=mode) as f:
            actual_contents = f.read()
            print(actual_contents)
            self.assertEqual(actual_contents, expected_contents)

    def assertBinaryFileContentsEqual(self, file_path: Path, expected_contents: bytes):
        self.assertFileContentsEqual(file_path, expected_contents, mode='rb')

    def assertNumberOfFilesInDirectory(self, dir: Path, expected: int):
        num_files = len(list(dir.iterdir()))
        self.assertEqual(num_files, expected)

    def assertNumLinesInFile(self, path: Path, expected: int):
        i = 0
        with path.open('r') as f:
            for i, l in enumerate(f.readlines()):
                pass
        self.assertEqual(i + 1, expected)
