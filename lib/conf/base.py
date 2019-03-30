import os
import shlex
import re
from inspect import getfullargspec
from collections import ChainMap
from tempfile import TemporaryDirectory

from dataclasses import dataclass, fields, Field, is_dataclass
from typing import NoReturn, Mapping, MutableMapping, Any, Iterable, Type


str_to_list = re.compile(r"^\s+|\s*,\s*|\s+$")


class ConfigMap(ChainMap):
    def get(self, key: str, **kwargs) -> Any:
        kwargs['default'] = None
        for mapping in self.maps:
            try:
                arg_spec = getfullargspec(mapping.get)
                if arg_spec.varkw or all(k in arg_spec.args for k in kwargs):
                    return mapping.get(key, **kwargs)
                return mapping.get(key)
            except KeyError:
                pass
        return None


@dataclass
class EnvironSection(dict):
    prefix: str
    section: str

    @property
    def full_prefix(self) -> str:
        return f"{self.prefix}_{self.section}".upper()

    def __getitem__(self, item, *args, **kwargs) -> Any:
        return os.environ.get(f"{self.full_prefix}_{item.upper()}")

    def __iter__(self) -> str:
        for item in os.environ.keys():
            if item.startswith(self.full_prefix):
                yield item.split(f"{self.full_prefix}_")[1].lower()


class EnvironConfig:

    @classmethod
    def with_defaults(cls):
        from lib import settings
        defaults = {
            'Testdir': settings.TESTS_DIR,
            'Develdir': settings.ROOT_DIR,
            'Userhome': settings.USER_HOME,
            "~": settings.USER_HOME,
            'Osdatadir': settings.OSDATA_DIR,
            'appname': settings.APP_NAME.replace(' ', '').lower(),
        }
        return cls(**defaults)

    def __init__(self, logger_name: str = 'root', **defaults):
        self.logger_name = logger_name
        self.defaults = defaults
        self.defaults['Tmpdir'] = TemporaryDirectory(prefix=defaults['appname'])

    def get_sections(self, cls: Type, section_name: Any) -> Mapping:
        return ConfigMap(
            EnvironSection(self.defaults['appname'], section_name),
        )

    def get_value(self, sections: Mapping, option: str, **kwargs) -> Any:
        return sections.get(option, **kwargs)

    def get_value_for_field(self, sections: Mapping, field: Field, logger=None) -> Any:
        config_kwargs = field.type.get('config_kwargs', {})
        value = self.get_value(sections, field.name, **config_kwargs)
        if isinstance(value, (str, int, float)):
            if is_dataclass(field.type):
                if field.type.get('config_from_section', True):
                    return self.configure_dataclass(field.type, value, logger=logger)
                else:
                    args = shlex.split(str(value))
                    if logger and 'logger' in [f.name for f in fields(field.type)]:
                        return field.type(*args, logger=logger)
                    return field.type(*args)
            elif issubclass(field.type, Iterable):
                return str_to_list.split(str(value))
            elif issubclass(field.type, Mapping):
                return self.get_mapping(value)
        return value

    def get_mapping(self, section_name: str) -> Mapping:
        return self.get_sections(Mapping, section_name)

    def get_config_for_dataclass(self, cls, sections: Mapping, logger=None) -> MutableMapping[str, Any]:
        return {name: value for name, value in
                [(field.name, self.get_value_for_field(sections, field, logger=logger)) for field in fields(cls)] if
                value is not None}

    def configure_dataclass(self, cls, section_name: str, logger=None, **kwargs) -> Any:
        sections = ConfigMap(kwargs, self.get_sections(cls, section_name))
        if hasattr(cls, 'swap_cls'):
            cls = self.get_value(sections, 'type')
            if isinstance(cls, str):
                cls = cls.swap_cls(cls)
        config = self.get_config_for_dataclass(cls, sections, logger=logger)
        if logger and 'logger' in [f.name for f in fields(cls)]:
            config['logger'] = logger
        return cls(**config)

    def configure_logging(self) -> NoReturn:
        pass
