from . import RawStr
from .base import BaseConfigClass
from .log_filters import BaseFilter
from configparser import ConfigParser, ExtendedInterpolation
from logging.config import fileConfig

from pathlib import Path
from typing import Mapping


class INIFileConfig(BaseConfigClass):

    def __init__(self, *file_names: Path, **kwargs):
        super(INIFileConfig, self).__init__(**kwargs)
        self.config = ConfigParser(defaults=self.defaults, interpolation=ExtendedInterpolation())
        self.config.read(file_names)

    @property
    def receiver(self) -> str:
        return self.config.get('Receiver', 'Type')

    @property
    def sender_type(self):
        return self.config.get('Sender', 'Type')

    @property
    def run_as(self):
        return self.config.get('MessageManager', 'run_as', fallback='asyncio')

    @property
    def message_manager_is_batch(self) -> bool:
        return self.config.getboolean('MessageManager', 'Batch', fallback=False)

    def get(self, section: str, option: str, data_type: type):
        if data_type == dict:
            try:
                return self.config[option.capitalize()]
            except KeyError:
                return None
        try:
            section = self.config[section]
        except KeyError:
            return None
        if data_type == bool:
            return section.getboolean(option, None)
        if data_type == RawStr:
            return section.get(option, None, raw=True)
        value = section.get(option, None)
        if data_type == tuple or data_type == list:
            if value:
                value = value.replace(', ', ',').split(',')
            elif value == '':
                value = ()
        if value is None or value == '':
            return None
        return data_type(value)

    def section_as_dict(self, section, **options) -> Mapping:
        d = {}
        for option, data_type in options.items():
            value = self.get(section, option, data_type)
            if value is not None:
                d[option] = value
        return d

    @property
    def protocol(self) -> str:
        return self.config.get('Protocol', 'Name')

    def get_home(self) -> Path:
        return Path(self.config.get('Dirs', 'Home'))

    def get_data_home(self) -> Path:
        return Path(self.config.get('Dirs', 'Data'))

    def get_action_home(self, action_name, d):
        return Path(
            self.config.get('Actions', '%sHome' % action_name, fallback=self.get_data_home().joinpath(d)))

    def configure_logging(self):
        configured = False
        while not configured:
            try:
                fileConfig(self.config)
                configured = True
            except FileNotFoundError as e:
                Path(e.filename).parent.mkdir(parents=True, exist_ok=True)
        for filter_name in self.get('filters', 'keys', tuple):
            BaseFilter.from_config(filter_name, cp=self)
