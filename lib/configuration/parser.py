from .base import BaseConfigClass
from lib.messagemanagers import MessageManager, BatchMessageManager
from lib import utils
import os

import configparser


class ConfigParserConfig(BaseConfigClass):

    def __init__(self, config_meta):
        super(ConfigParserConfig, self).__init__(config_meta)
        self.config = config_meta['config']

    def get_tuple(self, section, option):
        value = self.config.get(section, option, fallback='')
        if value:
            return tuple(value.split(','))
        return ()

    def get_path(self, section, option, fallback=''):
        path = self.config.get(section, option, fallback=fallback)
        if os.name == 'nt':
            path = path.replace('/', '\\')
        return path

    @property
    def receiver(self):
        return self.config.get('Receiver', 'Type')

    @property
    def message_manager(self):
        if self.config.getboolean('MessageManager', 'Batch', fallback=False):
            return BatchMessageManager
        return MessageManager

    @property
    def protocol(self):
        return self.config.get('Protocol', 'Name')

    @property
    def receiver_config(self):
        return {
            'host': self.config.get('Receiver', 'Host', fallback='127.0.0.1'),
            'port': self.config.getint('Receiver', 'Port', fallback=4000),
            'ssl': self.config.getboolean('Receiver', 'SSL', fallback=False),
            'ssl_cert': self.config.get('Receiver', 'SSLCert', fallback=''),
            'ssl_key': self.config.get('Receiver', 'SSLKey', fallback=''),
            'record': self.config.getboolean('Receiver', 'Record', fallback=False),
            'record_file': self.config.get('Receiver', 'RecordFile', fallback=''),
        }

    @property
    def protocol_config(self):
        return self.config['Protocol']

    @property
    def message_manager_config(self):
        return {
            'allowed_senders': self.get_tuple('MessageManager', 'AllowedSenders'),
            'aliases': self.config['Aliases'],
            'actions': self.get_tuple('Actions', 'Types'),
            'print_actions': self.get_tuple('Print', 'Types'),
            'generate_timestamp': self.config.getboolean('MessageManager', 'GenerateTimestamp', fallback=False)
        }

    def action_config(self, app_name, action_name, storage=True):
        section_name = 'Actions' if storage else 'Print'
        return {
            'home': self.get_path(section_name, 'Home', fallback=utils.data_directory(app_name)),
            'data_dir': self.config.get(section_name, '%s_data_dir' % action_name, fallback=''),
        }


class ConfigParserFile(ConfigParserConfig):

    def __init__(self, config_meta):
        config_meta['config'] = configparser.ConfigParser()
        config_meta['config'].read(config_meta['filename'])
        super(ConfigParserFile, self).__init__(config_meta)
