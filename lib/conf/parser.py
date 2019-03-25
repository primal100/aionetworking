from .types import RawStr, BaseSwappable
from .base import BaseConfig
from .log_filters import BaseFilter
from configparser import ConfigParser, ExtendedInterpolation
from logging.config import fileConfig

from pathlib import Path
from typing import MutableMapping, Iterable, Any, NoReturn
from dataclasses import Field


class INIFileConfig(BaseConfig):

    def __init__(self, *file_names: Path, **kwargs):
        super().__init__(**kwargs)
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read_dict({'Dirs': self.defaults})
        self.config.read(file_names)
        additional_config_files = list(self.config['ConfigFiles'].values())
        self.config.read(additional_config_files)

    @property
    def receiver(self) -> str:
        return self.config.get('Receiver', 'Type')

    @property
    def sender_type(self) -> str:
        return self.config.get('Sender', 'Type')

    def get(self, section: str, option: str, data_type: type) -> Any:
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
        if value is None or value == '':
            return None
        if issubclass(data_type, BaseSwappable):
            return data_type.swap_from_config(value)
        return data_type(value)

    def section_as_dict(self, section: str, fields=Iterable[Field]) -> MutableMapping[str, Any]:
        d = {}
        for field in fields:
            type_depends_on = field.metadata.get('type_depends_on', None)
            factory = field.metadata.get('factory', None)
            if type_depends_on:
                data_type = d[type_depends_on]
            elif factory:
                data_type = factory
            else:
                data_type = field.type
            value = self.get(section, field.name, data_type)
            if value is not None:
                d[field.name] = value
        return d

    @property
    def protocol(self) -> str:
        return self.config.get('Protocol', 'Name')

    def configure_logging(self) -> NoReturn:
        configured = False
        while not configured:
            try:
                fileConfig(self.config)
                configured = True
            except FileNotFoundError as e:
                Path(e.filename).parent.mkdir(parents=True, exist_ok=True)
        for filter_name in self.get('filters', 'keys', tuple):
            BaseFilter.from_config(section_postfix=filter_name, cp=self)
