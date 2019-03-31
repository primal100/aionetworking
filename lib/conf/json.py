from collections import ChainMap
from pathlib import Path

from .mapping import MappingConfig

from typing import AnyStr


class JSONConfig(MappingConfig):

    def __init__(self, *jsons: AnyStr, **kwargs):
        config = ChainMap(*[self.get_mapping(json) for json in jsons])
        super().__init__(config, **kwargs)

    def get_mapping(self, json: AnyStr):
        formatted = json.format_map(self.defaults)
        return json.loads(formatted)

    def add_json(self, json: AnyStr):
        map = self.get_mapping(json)
        self.add_mapping(map)


class JSONFileConfig(JSONConfig):

    def __init__(self, *file_names: Path, **kwargs):
        jsons = [self.read_file(path) for path in file_names]
        super().__init__(*jsons, **kwargs)
        additional_config_files = list(self.config['ConfigFiles'].values())
        for f in additional_config_files:
            json = self.read_file(Path(f))
            self.add_json(json)

    def read_file(self, file_name: Path):
        return file_name.read_text()


class JSONBFileConfig(JSONConfig):

    def read_file(self, file_name: Path):
        return file_name.read_bytes()