from configparser import ConfigParser, ExtendedInterpolation
from logging.config import fileConfig
from pathlib import Path

from .mapping import MappingConfig


class INIFileConfig(MappingConfig):
    log_config = fileConfig

    def __init__(self, *file_names: Path, **kwargs):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.read_dict({'Dirs': self.defaults})
        config.read(file_names)
        additional_config_files = list(self.config['ConfigFiles'].values())
        config.read(additional_config_files)
        super().__init__(config, **kwargs)

