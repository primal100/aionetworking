from .base import BaseConfigClass
from configparser import ConfigParser, ExtendedInterpolation
from logging.config import fileConfig

from pathlib import Path
from typing import Mapping


class INIFileConfig(BaseConfigClass):

    def __init__(self, filename: Path, postfix: str='receiver'):
        super(INIFileConfig, self).__init__(postfix=postfix)
        self.config = ConfigParser(defaults=self.defaults, interpolation=ExtendedInterpolation())
        #self.config.optionxform = str
        self.config.read(filename)

    @property
    def receiver(self) -> str:
        return self.config.get('Receiver', 'Type')

    @property
    def receiver_config(self) -> Mapping:
        return {
            'host': self.config.get('Receiver', 'Host', fallback='127.0.0.1'),
            'port': self.config.getint('Receiver', 'Port', fallback=4000),
            'ssl': self.config.getboolean('Receiver', 'SSL', fallback=False),
            'ssl_cert': self.config.get('Receiver', 'SSLCert', fallback=''),
            'ssl_key': self.config.get('Receiver', 'SSLKey', fallback=''),
            'record': self.config.getboolean('Receiver', 'Record', fallback=False),
            'record_file': self.config.getpath('Receiver', 'RecordFile', fallback=''),
            'allow_scp': self.config.getboolean('Receiver', 'AllowSCP', fallback=False),
            'base_upload_dir': self.config.getpath('Receiver', 'BaseSFTPDIR',
                                                   fallback=self.data_home.joinpath("Uploads")),
            'logins': dict(self.config.items('Logins', raw=True))
        }

    @property
    def client_config(self) -> Mapping:
        return {
            'src_ip': self.config.get('Sender', 'SrcIP', fallback=''),
            'src_port': self.config.getint('Sender', 'SrcPort', fallback=0),
        }

    @property
    def message_manager_is_batch(self) -> bool:
        return self.config.getboolean('MessageManager', 'Batch', fallback=False)

    def get(self, section: str, option: str, data_type: type):
        if data_type == dict:
            try:
                return self.config[option.capitalize()].items()
            except KeyError:
                return None
        try:
            section = self.config[section]
        except KeyError:
            return None
        if data_type == bool:
            return section.getboolean(option, None)
        value = section.get(option, None)
        if value is not None and data_type == tuple or data_type == list:
            value = value.replace(', ', ',').split(',')
        if value is None:
            return value
        return data_type(value)

    def section_as_dict(self, section, **options) -> Mapping:
        d = {}
        for option, data_type in options.items():
            value = self.get(section, option, data_type)
            if value is not None:
                d[option] = value
        return d

    @property
    def message_manager_config(self) -> Mapping:
        return {
            'allowed_senders': self.config.gettuple('MessageManager', 'AllowedSenders'),
            'aliases': self.config['Aliases'],
            'actions': self.config.gettuple('Actions', 'Types'),
            'print_actions': self.config.gettuple('Print', 'Types'),
            'generate_timestamp': self.config.getboolean('MessageManager', 'GenerateTimestamp', fallback=False),
            'interval': self.config.getint('MessageManager', 'Interval', fallback=5)
        }

    @property
    def protocol(self) -> str:
        return self.config.get('Protocol', 'Name')

    @property
    def protocol_config(self) -> Mapping:
        return self.config['Protocol'].items()

    def get_home(self) -> Path:
        return Path(self.config.get('Dirs', 'Home'))

    def get_data_home(self) -> Path:
        return Path(self.config.get('Dirs', 'Data'))

    def get_action_home(self, action_name: str) -> Path:
        return Path(
            self.config.get('Actions', '%sHome' % action_name, fallback=self.get_data_home().joinpath(action_name)))

    def configure_logging(self):
        configured = False
        while not configured:
            try:
                fileConfig(self.config)
                configured = True
            except FileNotFoundError as e:
                Path(e.filename).parent.mkdir(parents=True, exist_ok=True)
