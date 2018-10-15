from .base import BaseConfigClass
from lib.messagemanagers import MessageManager, BatchMessageManager
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

    @property
    def receiver(self):
        return self.config.get('Receiver', 'Type')

    @property
    def message_manager(self):
        if self.config.getboolean('MessageManager', 'Batch', fallback=False):
            return BatchMessageManager
        return MessageManager

    @property
    def interface(self):
        return self.config.get('Interface', 'Name')

    @property
    def interface_config(self):
        return self.config['Interface']

    @property
    def message_manager_config(self):
        return {
            'allowed_senders': self.get_tuple('MessageManager', 'AllowedSenders'),
            'aliases': self.config['Aliases'],
            'actions': self.get_tuple('Actions', 'Types'),
            'print_actions': self.get_tuple('Print', 'Types'),
            'generate_timestamp': self.config.getboolean('MessageManager', 'GenerateTimestamp', fallback=False)
        }

    def action_config(self, action_name, storage=True):
        section_name = 'Actions' if storage else 'Print'
        return {
            'home': self.config.get(section_name, 'Home', fallback=''),
            'data_dir': self.config.get(section_name, '%s_data_dir' % action_name, fallback=''),
        }


class ConfigParserFile(ConfigParserConfig):

    def __init__(self, config_meta):
        config_meta['config'] = configparser.ConfigParser()
        config_meta['config'].read(self.config_meta['filename'])
        super(ConfigParserFile, self).__init__(config_meta)
