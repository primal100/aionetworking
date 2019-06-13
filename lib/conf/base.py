import os
import re
import shlex
from inspect import getfullargspec
from collections import ChainMap
from tempfile import TemporaryDirectory
from dataclasses import dataclass, fields, Field

import pydantic

from lib.receivers.base import BaseReceiver
from lib.senders.base import BaseSender
from lib.utils import str_to_list

from typing import NoReturn, Mapping, MutableMapping, Any, Iterable, Type, Union, Optional


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

    def __eq__(self, other):
        return True

    def __init__(self, **defaults):
        self.defaults = defaults
        self.defaults['Tmpdir'] = TemporaryDirectory(prefix=defaults['appname'])

    def _get_sections(self, cls: Type, section_name: Any) -> Mapping:
        return ConfigMap(
            EnvironSection(self.defaults['appname'], section_name),
        )

    def _get_value(self, sections: Mapping, option: str, **kwargs) -> Any:
        return sections.get(option, **kwargs)

    def is_model(self, cls: Type) -> bool:
        return isinstance(cls, pydantic.BaseModel)

    def _get_type(self, cls: Type, sections: Mapping) -> Any:
        return self._get_value(sections, 'type')

    def swap(self, new_cls: Union[Type, str], cls: Type):
        if hasattr(cls, 'swap_cls'):
            if isinstance(new_cls, (int, float, str)):
                return cls.swap_cls(new_cls)
            return new_cls
        return cls

    def _get_value_for_field(self, sections: Mapping, field: Field, logger=None) -> Any:
        if field.name.startswith('_'):
            return None
        config_kwargs = field.type.get('config_kwargs', {})
        value = self._get_value(sections, field.name, **config_kwargs)
        return self._process_value(value, field.type, logger=logger)

    def _process_value(self, value: Any, type_: type, logger=None) -> Any:
        if isinstance(value, (str, int, float)):
            if hasattr(type_, '__pydantic_model__'):
                return self.configure_model(type_, value, logger=logger, model=type_.__pydantic_model__)
            elif self.is_model(type_):
                return self.configure_model(type_, value, logger=logger)
            elif issubclass(type_, Iterable):
                return str_to_list.split(str(value))
            elif issubclass(type_, Mapping):
                return self.get_mapping(value)
        return value

    def _get_object(self, cls, name, **kwargs) -> Any:
        return self._process_value(name, cls, **kwargs)

    def _get_config(self, cls: Type, prefix: Optional[str] = None, name: Optional[str] = None) -> Any:
        if name and prefix:
            section_name = f"{prefix}_{name}"
        elif name:
            section_name = name
        else:
            section_name = prefix
        return self._get_object(cls, section_name)

    def get_mapping(self, section_name: str) -> Mapping:
        return self._get_sections(Mapping, section_name)

    def _get_config_for_fields(self, model_fields, sections: Mapping, logger=None) -> MutableMapping[str, Any]:
        return {name: value for name, value in
                [(field.name, self._get_value_for_field(sections, field, logger=logger)) for field in model_fields] if
                value is not None}

    def _get_config_for_model(self, cls: pydantic.BaseModel, sections: Mapping, logger=None) -> MutableMapping[str, Any]:
        model_fields = cls.fields.values()
        return self._get_config_for_fields(model_fields, sections, logger=logger)

    def configure_model(self, cls, value: str, *args, logger=None, model=None, **kwargs) -> Any:
        if getattr(cls, 'config_from_string', False):
            args = shlex.split(str(value))
        elif getattr(cls, 'swap_from_string', False):
            cls = self.swap(value, cls)
        else:
            sections = ConfigMap(kwargs, self._get_sections(cls, value))
            cls = self.swap(sections['type'], cls)
            model = model or cls.__pydantic__model
            config = self._get_config_for_model(model, sections, logger=logger)
            kwargs.update(config)
        if logger and 'logger' in [f.name for f in fields(cls)]:
            kwargs['logger'] = logger
        return cls(*args, **kwargs)

    def get_receiver(self, name: Optional[str] = None) -> BaseReceiver:
        return self._get_config(BaseReceiver, prefix='Receiver', name=name)

    def get_sender(self, name) -> BaseSender:
        return self._get_config(BaseSender, prefix='Sender', name=name)

    def configure_logging(self) -> NoReturn:
        pass
