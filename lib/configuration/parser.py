from .base import BaseConfigClass
from lib.messagemanagers import MessageManager, BatchMessageManager

import configparser


class INIFileConfig(BaseConfigClass):

    def __init__(self, app_name, filename, postfix='receiver'):
        self.config = configparser.RawConfigParser()
        self.config.optionxform = str
        self.config.read(filename)
        super(INIFileConfig, self).__init__(app_name, postfix=postfix)

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
            'record_file': self.get_full_path(self.config.get('Receiver', 'RecordFile', fallback='')),
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

    def log_config(self):
        config = dict(self.config.items('Logging', raw=True))
        formatter_dict = {}
        handler_dict = {'formatter': 'standard'}
        for k, v in config.items():
            if k == 'format':
                formatter_dict['format'] = v
            elif k == 'datefmt':
                formatter_dict['datafmt'] = v
            elif k == 'handler':
                handler_dict['class'] = "logging." + v
            elif k == 'filename':
                handler_dict['filename'] = self.get_full_path(v)
            else:
                try:
                    handler_dict[k] = self.config.getint('Logging', k)
                except ValueError:
                    try:
                        handler_dict[k] = self.config.getboolean('Logging', k)
                    except ValueError:
                        handler_dict[k] = v

        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': formatter_dict
            },
            'handlers': {
                'default': handler_dict
            },
            'loggers': {
                '': {
                    'handlers': ['default'],
                    'level': config['level'],
                    'propagate': True
                },
                'messageManager': {
                    'handlers': ['default'],
                    'level': config['level'],
                    'propagate': False
                },
            }
        }

    def get_home(self, fallback='%(userhome)s/%(appname)s'):
        return self.config.get('Application', 'Home', fallback=fallback, raw=True)

    def get_data_home(self, fallback='%(home)s/data'):
        return self.config.get('Actions', 'DataHome', fallback=fallback)

    def get_action_home(self, action_name, fallback='%(datahome)s/%(actionname)s'):
        return self.config.get('Actions', '%sHome' % action_name, fallback=fallback)
