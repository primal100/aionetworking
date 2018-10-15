import os
import configparser
from unittest import TestCase

from lib.configuration.parser import ConfigParserConfig
import definitions
from logging.config import fileConfig

log_config_path = os.path.join(definitions.TEST_CONF_DIR, 'logging.ini')

logging_setup = False
while not logging_setup:
    try:
        fileConfig(log_config_path)
        logging_setup = True
    except FileNotFoundError as e:
        log_directory = os.path.dirname(e.filename)
        os.makedirs(log_directory, exist_ok=True)


class BaseTestCase(TestCase):
    maxDiff = None
    base_home = definitions.TEST_DATA_DIR


    def prepare_config(self):
        config = configparser.ConfigParser()
        config.add_section('Receiver')
        config.add_section('MessageManager')
        config.add_section('Interface')
        config.add_section('Actions')
        config.add_section('Print')
        config.add_section('Aliases')
        config.set('MessageManager', 'Batch', 'False')
        config.set('MessageManager', 'AllowedSenders', '10.10.10.10')
        config.set('MessageManager', 'GenerateTimestamp', 'False')
        config.set('Interface', 'Name', 'TCAP')
        config.set('Actions', 'Home', self.base_home)
        config.set('Actions', 'Types', 'binary,decode,prettify,summarise')
        config.set('Print', 'Types', 'binary,decode,prettify,summarise')
        return ConfigParserConfig({'config': config})

    def assertPathEqual(self, expected, actual):
        self.assertEqual(os.path.normpath(expected), os.path.normpath(actual))

    def assertPathExists(self, path):
        self.assertTrue(os.path.exists(path))

    def assertFileContentsEqual(self, file_path, expected_contents, mode='r'):
        self.assertPathExists(file_path)
        with open(file_path, mode) as f:
            actual_contents = f.read()
            self.assertEqual(actual_contents, expected_contents)

    def assertBinaryFileContentsEqual(self, file_path, expected_contents):
        self.assertPathExists(file_path)
        self.assertFileContentsEqual(file_path, expected_contents, mode='rb')
