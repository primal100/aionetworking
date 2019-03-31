import os
import shlex
import re
from inspect import getfullargspec
from collections import ChainMap
from tempfile import TemporaryDirectory
from dataclasses import dataclass, fields, Field, is_dataclass

import pydantic

from typing import NoReturn, Mapping, MutableMapping, Any, Iterable, Type, Union


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

    def add_after(self, *args: Mapping):
        for mapping in args:
            self.maps.append(mapping)

    def add_before(self, *args: Mapping):
        for mapping in args:
            self.maps.insert(0, mapping)


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

    def is_dataclass(self, cls: Type):
        return is_dataclass(cls)

    def is_model(self, cls: Type):
        return isinstance(cls, pydantic.BaseModel)

    def get_type(self, cls: Type, sections: Mapping):
        return self.get_value(sections, 'type')

    def swap(self, new_cls: Union[Type, str], cls: Type):
        if hasattr(cls, 'swap_cls'):
            if isinstance(new_cls, (int, float, str)):
                return cls.swap_cls(new_cls)
            return new_cls
        return cls

    def get_value_for_field(self, sections: Mapping, field: Field, logger=None) -> Any:
        if field.name.startswith('_'):
            return None
        config_kwargs = field.type.get('config_kwargs', {})
        value = self.get_value(sections, field.name, **config_kwargs)
        if isinstance(value, (str, int, float)):
            if self.is_dataclass(field.type):
                return self.configure_dataclass(field.type, value, logger=logger)
            elif self.is_model(field.type):
                return self.configure_model(field.type, value, logger=logger)
            elif issubclass(field.type, Iterable):
                return str_to_list.split(str(value))
            elif issubclass(field.type, Mapping):
                return self.get_mapping(value)
        return value

    def get_mapping(self, section_name: str) -> Mapping:
        return self.get_sections(Mapping, section_name)

    def get_config_for_fields(self, model_fields, sections: Mapping, logger=None) -> MutableMapping[str, Any]:
        return {name: value for name, value in
                [(field.name, self.get_value_for_field(sections, field, logger=logger)) for field in model_fields] if
                value is not None}

    def get_config_for_dataclass(self, cls, sections: Mapping, logger=None) -> MutableMapping[str, Any]:
        dc_fields = fields(cls)
        return self.get_config_for_fields(dc_fields, sections, logger=logger)

    def get_config_for_model(self, cls: pydantic.BaseModel, sections: Mapping, logger=None) -> MutableMapping[str, Any]:
        model_fields = cls.fields.values()
        return self.get_config_for_fields(model_fields, sections, logger=logger)

    def configure_dataclass(self, cls, value: str, *args, logger=None, **kwargs) -> Any:
        if getattr(cls, 'config_from_string', False):
            args = shlex.split(str(value))
        elif getattr(cls, 'swap_from_string', False):
            cls = self.swap(value, cls)
        else:
            sections = ConfigMap(kwargs, self.get_sections(cls, value))
            cls = self.swap(sections['type'], cls)
            config = self.get_config_for_dataclass(cls, sections, logger=logger)
            kwargs.update(config)
        if logger and 'logger' in [f.name for f in fields(cls)]:
            kwargs['logger'] = logger
        return cls(*args, **kwargs)

    def configure_logging(self) -> NoReturn:
        pass
