import configparser
from unittest import TestCase

from lib.conf.parser import INIFileConfig
import definitions


class BaseTestCase(TestCase):
    maxDiff = None
    base_data_dir = definitions.TEST_DATA_DIR

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
        return INIFileConfig({'config': config})


    def assertFileContentsEqual(self, file_path, expected_contents, mode='r'):
        self.assertTrue(file_path.exists())
        with file_path.open() as f:
            actual_contents = f.read()
            self.assertEqual(actual_contents, expected_contents)

    def assertBinaryFileContentsEqual(self, file_path, expected_contents):
        self.assertFileContentsEqual(file_path, expected_contents, mode='rb')
