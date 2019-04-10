from logging.config import dictConfig
from pathlib import Path

from .base import EnvironConfig, ConfigMap
from .log_filters import BaseFilter

from typing import Type, Any, Mapping, MutableMapping, NoReturn


class MappingConfig(EnvironConfig):
    log_config = dictConfig

    def __eq__(self, other):
        return dict(self.config) == dict(other.config) and self.environ_priority == other.environ_priority

    def __init__(self, config: MutableMapping, environ_priority: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.environ_priority = environ_priority

    def add_mapping(self, mapping: Mapping):
        self.config.update(mapping)

    def _get_sections(self, cls: Type, section_name: Any) -> Mapping:
        environ = super()._get_sections(cls, section_name)
        cp = self.config[section_name]
        if self.environ_priority:
            return ConfigMap(environ, cp)
        return ConfigMap(cp, environ)

    def configure_filters(self):
        for filter_name in self.config.get('filters', 'keys').split(','):
            section_name = f"Filter_{filter_name}"
            self._process_value(section_name, BaseFilter)

    def configure_logging(self) -> NoReturn:
        configured = False
        while not configured:
            try:
                self.log_config(self.config.get('logging', {}))
                configured = True
            except FileNotFoundError as e:
                Path(e.filename).parent.mkdir(parents=True, exist_ok=True)
        self.configure_filters()
