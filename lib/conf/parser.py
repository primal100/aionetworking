from configparser import ConfigParser, ExtendedInterpolation
from logging.config import fileConfig
from pydantic.types import FilePath

from .mapping import MappingConfig


class INIFileConfig(MappingConfig):
    log_config = fileConfig

    def __init__(self, *file_names: FilePath, **kwargs):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.read_dict({'Dirs': self.defaults})
        config.read(file_names)
        additional_config_files = list(config['ConfigFiles'].values())
        config.read(additional_config_files)
        super().__init__(config, **kwargs)

