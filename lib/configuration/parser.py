from .base import BaseConfigClass
from lib.messagemanagers import MessageManager, BatchMessageManager

from configparser import ConfigParser, ExtendedInterpolation
import os
import pathlib
from logging.config import fileConfig


def get_tuple(v):
    return tuple(v.split(','))

def get_path(v):
    return pathlib.PurePath(v)


converters = {
    'tuple': get_tuple,
    'path': get_path
}


class INIFileConfig(BaseConfigClass):

    def __init__(self, app_name, filename, postfix='receiver'):
        super(INIFileConfig, self).__init__(app_name, postfix=postfix)
        self.config = ConfigParser(defaults=self.defaults, interpolation=ExtendedInterpolation(),
                                   converters=converters)
        self.config.optionxform = str
        self.config.read(filename)





    """def get_tuple(self, section, option):
        value = self.config.get(section, option, fallback='')
        if value:
            return tuple(value.split(','))
        return ()"""

    @property
    def receiver(self):
        return self.config.get('Receiver', 'Type')

    @property
    def receiver_config(self):
        return {
            'host': self.config.get('Receiver', 'Host', fallback='127.0.0.1'),
            'port': self.config.getint('Receiver', 'Port', fallback=4000),
            'ssl': self.config.getboolean('Receiver', 'SSL', fallback=False),
            'ssl_cert': self.config.get('Receiver', 'SSLCert', fallback=''),
            'ssl_key': self.config.get('Receiver', 'SSLKey', fallback=''),
            'record': self.config.getboolean('Receiver', 'Record', fallback=False),
            'record_file': self.config.getpath('Receiver', 'RecordFile', fallback=''),
        }

    @property
    def client_config(self):
        return {
            'src_ip': self.config.get('Sender', 'SrcIP', fallback=''),
            'src_port': self.config.getint('Sender', 'SrcPort', fallback=0),
        }

    @property
    def message_manager(self):
        if self.config.getboolean('MessageManager', 'Batch', fallback=False):
            return BatchMessageManager
        return MessageManager

    @property
    def message_manager_config(self):
        return {
            'allowed_senders': self.config.gettuple('MessageManager', 'AllowedSenders'),
            'aliases': self.config['Aliases'],
            'actions': self.config.gettuple('Actions', 'Types'),
            'print_actions': self.config.gettuple('Print', 'Types'),
            'generate_timestamp': self.config.getboolean('MessageManager', 'GenerateTimestamp', fallback=False)
        }

    @property
    def protocol(self):
        return self.config.get('Protocol', 'Name')

    @property
    def protocol_config(self):
        return self.config['Protocol']

    def get_home(self):
        return self.config.getpath('Dirs', 'Home')

    def get_data_home(self):
        return self.config.getpath('Dirs', 'Data')

    def get_action_home(self, action_name):
        return self.config.getpath('Actions', '%sHome' % action_name,
                                   fallback=os.path.join(self.data_home, action_name))

    def configure_logging(self):
        configured = False
        while not configured:
            try:
                fileConfig(self.config)
                configured = True
            except FileNotFoundError as e:
                os.makedirs(os.path.dirname(e.filename), exist_ok=True)
