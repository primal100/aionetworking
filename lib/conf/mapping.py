from logging.config import dictConfig
from pathlib import Path

from .base import EnvironConfig, ConfigMap
from .log_filters import BaseFilter

from typing import Type, Any, Mapping, NoReturn


class MappingConfig(EnvironConfig):
    log_config = dictConfig

    def __init__(self, config: Mapping, environ_priority: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.environ_priority = environ_priority

    def get_sections(self, cls: Type, section_name: Any) -> Mapping:
        environ = super().get_sections(cls, section_name)
        cp = self.config[section_name]
        if self.environ_priority:
            return ConfigMap(environ, cp)
        return ConfigMap(cp, environ)

    def configure_filters(self):
        for filter_name in self.config.get('filters', 'keys').split(','):
            BaseFilter.from_config(section_postfix=filter_name, cp=self)

    def configure_logging(self) -> NoReturn:
        configured = False
        while not configured:
            try:
                self.log_config(self.config.get('logging', {}))
                configured = True
            except FileNotFoundError as e:
                Path(e.filename).parent.mkdir(parents=True, exist_ok=True)
        self.configure_filters()
